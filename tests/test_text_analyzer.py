import pytest
from narratix.core.analysis.text_analyzer import TextAnalyzer

@pytest.mark.asyncio
async def test_text_analyzer():
    analyzer = TextAnalyzer()
    text = "This is a test narrative."
    
    # Test initial analysis
    result = await analyzer.analyze_text(text)
    assert "roles" in result
    assert "narrative_elements" in result
    assert "meta" in result
    assert result["meta"]["word_count"] == 5
    
    # Test caching
    cached_result = await analyzer.analyze_text(text)
    assert cached_result == result
    
    # Test force reanalysis
    force_result = await analyzer.analyze_text(text, force_reanalysis=True)
    assert force_result == result  # Should be same since analysis is deterministic 