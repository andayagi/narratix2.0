#!/usr/bin/env python3
import os
import argparse
import librosa
import soundfile as sf
import numpy as np
from scipy import signal
from pathlib import Path

def spectral_gate(audio_path, output_path, threshold_db=-30, smoothing=0.05):
    """
    Apply spectral gating for noise reduction - gentler than Wiener filter
    threshold_db: threshold in dB below which to gate the audio
    smoothing: amount of smoothing to apply to the gate
    """
    # Load audio
    y, sr = librosa.load(audio_path, sr=None)
    
    # Compute STFT
    D = librosa.stft(y)
    
    # Convert to power spectrogram
    mag, phase = librosa.magphase(D)
    
    # Compute noise profile from the first 100ms assuming it's noise
    noise_length = min(int(sr * 0.1), len(y))
    noise_spec = np.mean(np.abs(librosa.stft(y[:noise_length]))**2, axis=1)
    noise_spec = noise_spec[:, np.newaxis]
    
    # Compute threshold
    threshold = 10**(threshold_db/10) * noise_spec
    
    # Apply spectral gate
    mask = (mag**2 > threshold)
    
    # Apply smoothing to the mask
    if smoothing > 0:
        # Simple temporal smoothing
        smoothing_filter = np.ones(3) / 3
        for i in range(mask.shape[0]):
            mask[i, :] = signal.convolve(mask[i, :], smoothing_filter, mode='same')
    
    # Apply mask and phase
    mag_gated = mag * mask
    D_gated = mag_gated * phase
    
    # Inverse STFT
    y_gated = librosa.istft(D_gated)
    
    # Write output
    sf.write(output_path, y_gated, sr)
    return output_path

def reduce_noise_wiener(audio_path, output_path, wiener_size=5):
    """Apply gentle Wiener filter to reduce background noise"""
    y, sr = librosa.load(audio_path, sr=None)
    # Apply Wiener filter with smaller window size for less blurring
    denoised = signal.wiener(y, mysize=wiener_size)
    sf.write(output_path, denoised, sr)
    return output_path

def normalize_volume(audio_path, output_path, target_rms=-18.0):
    """Normalize the volume of audio to target RMS level"""
    y, sr = librosa.load(audio_path, sr=None)
    rms = np.sqrt(np.mean(y**2))
    
    # If RMS is too low or audio is silent, avoid excessive amplification
    if rms < 1e-6:
        print("Warning: Audio has very low volume. Minimal normalization applied.")
        gain = min(10.0, 10**(-18/20) / 1e-6)  # Cap gain to 10x
    else:
        # Convert to dB and calculate gain needed
        gain = 10**(0.05 * (target_rms - 20 * np.log10(rms)))
    
    normalized = y * gain
    sf.write(output_path, normalized, sr)
    return output_path

def remove_clicks(audio_path, output_path, threshold=0.3, window_size=5):
    """Remove clicks and pops from audio with gentler thresholds"""
    y, sr = librosa.load(audio_path, sr=None)
    
    # Detect sharp peaks in the derivative of the signal
    derivative = np.diff(y)
    # Find indices where derivative exceeds threshold
    click_indices = np.where(np.abs(derivative) > threshold)[0]
    
    # If clicks are found, smooth them out
    if len(click_indices) > 0:
        print(f"Found {len(click_indices)} potential clicks/pops to fix")
        for i in click_indices:
            if i > window_size and i < len(y) - window_size:
                # Use a wider interpolation window
                window = np.hanning(window_size * 2 + 1)
                window = window / np.sum(window)
                segment = y[i-window_size:i+window_size+1]
                y[i] = np.sum(segment * window)
    
    sf.write(output_path, y, sr)
    return output_path

def adaptive_noise_reduction(audio_path, output_path, reduction_amount=0.5):
    """Use adaptive thresholding to reduce noise while preserving voice"""
    y, sr = librosa.load(audio_path, sr=None)
    
    # Compute spectrogram
    S_full = librosa.stft(y)
    
    # Compute magnitude spectrogram
    S_mag = np.abs(S_full)
    
    # Compute noise threshold
    noise_threshold = np.median(S_mag) * reduction_amount
    
    # Apply soft thresholding
    S_reduced = S_full * (S_mag > noise_threshold)
    
    # Reconstruct signal
    y_reduced = librosa.istft(S_reduced)
    
    sf.write(output_path, y_reduced, sr)
    return output_path

def process_audio(input_file, output_file, temp_dir=None, method="gentle"):
    """Process audio through a series of cleanup stages"""
    print(f"Processing {input_file} -> {output_file} (Method: {method})")
    
    if temp_dir is None:
        temp_dir = os.path.dirname(output_file)
    
    Path(temp_dir).mkdir(parents=True, exist_ok=True)
    
    # Create temporary files for each processing stage
    temp_denoised = os.path.join(temp_dir, "temp_denoised.wav")
    temp_clicks_removed = os.path.join(temp_dir, "temp_clicks_removed.wav")
    temp_normalized = os.path.join(temp_dir, "temp_normalized.wav")
    
    try:
        # Apply processing chain with appropriate method
        if method == "spectral":
            print("1. Applying spectral gate for noise reduction...")
            spectral_gate(input_file, temp_denoised, threshold_db=-30, smoothing=0.05)
        elif method == "adaptive":
            print("1. Applying adaptive noise reduction...")
            adaptive_noise_reduction(input_file, temp_denoised, reduction_amount=0.3)
        else:  # gentle
            print("1. Applying gentle Wiener filter...")
            reduce_noise_wiener(input_file, temp_denoised, wiener_size=5)
        
        print("2. Removing clicks and pops...")
        remove_clicks(temp_denoised, temp_clicks_removed, threshold=0.3, window_size=5)
        
        print("3. Normalizing volume...")
        normalize_volume(temp_clicks_removed, output_file)
        
        print(f"Processing complete. Output saved to {output_file}")
        
    finally:
        # Clean up temporary files
        for temp_file in [temp_denoised, temp_clicks_removed, temp_normalized]:
            if os.path.exists(temp_file):
                os.remove(temp_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean audio glitches from Hume API generated audio")
    parser.add_argument("input_file", help="Path to input audio file")
    parser.add_argument("--output_file", help="Path to output audio file (default: input_file_method.mp3)")
    parser.add_argument("--method", choices=["gentle", "spectral", "adaptive"], default="gentle",
                        help="Noise reduction method: gentle (default), spectral, or adaptive")
    
    args = parser.parse_args()
    
    # Default output filename if not specified
    if args.output_file is None:
        input_path = Path(args.input_file)
        file_stem = input_path.stem
        args.output_file = str(input_path.with_name(f"{file_stem}_{args.method}{input_path.suffix}"))
    
    process_audio(args.input_file, args.output_file, method=args.method) 