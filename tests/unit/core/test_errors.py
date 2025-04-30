import pytest
from src.narratix.core import errors

def test_raise_narratix_error():
    """Test raising and catching the base NarratixError."""
    with pytest.raises(errors.NarratixError):
        raise errors.NarratixError("A base error occurred")

def test_raise_configuration_error():
    """Test raising and catching ConfigurationError."""
    with pytest.raises(errors.ConfigurationError) as excinfo:
        raise errors.ConfigurationError("Config file missing")
    assert "Config file missing" in str(excinfo.value)
    assert isinstance(excinfo.value, errors.NarratixError)

def test_raise_domain_error():
    """Test raising and catching DomainError."""
    with pytest.raises(errors.DomainError) as excinfo:
        raise errors.DomainError("Invalid state")
    assert "Invalid state" in str(excinfo.value)
    assert isinstance(excinfo.value, errors.NarratixError)

def test_raise_infrastructure_error():
    """Test raising and catching InfrastructureError."""
    with pytest.raises(errors.InfrastructureError) as excinfo:
        raise errors.InfrastructureError("Database connection failed")
    assert "Database connection failed" in str(excinfo.value)
    assert isinstance(excinfo.value, errors.NarratixError)

def test_raise_validation_error():
    """Test raising and catching ValidationError."""
    with pytest.raises(errors.ValidationError) as excinfo:
        raise errors.ValidationError("Email format invalid")
    assert "Email format invalid" in str(excinfo.value)
    # Check inheritance
    assert isinstance(excinfo.value, errors.DomainError)
    assert isinstance(excinfo.value, errors.NarratixError)

def test_raise_not_found_error():
    """Test raising and catching NotFoundError."""
    with pytest.raises(errors.NotFoundError) as excinfo:
        raise errors.NotFoundError("User ID 123 not found")
    assert "User ID 123 not found" in str(excinfo.value)
    # Check inheritance
    assert isinstance(excinfo.value, errors.InfrastructureError)
    assert isinstance(excinfo.value, errors.NarratixError)

def test_catch_specific_error():
    """Test catching a specific error doesn't catch its parent unexpectedly."""
    try:
        raise errors.ValidationError("Specific validation issue")
    except errors.NotFoundError:
        pytest.fail("Caught NotFoundError when ValidationError was expected")
    except errors.ValidationError:
        pass # Expected
    except errors.DomainError:
        pytest.fail("Caught DomainError directly when ValidationError was expected")
    except errors.NarratixError:
        pytest.fail("Caught NarratixError directly when ValidationError was expected")
    except Exception:
        pytest.fail("Caught generic Exception")

def test_catch_parent_error():
    """Test catching a parent error type catches its children."""
    try:
        raise errors.ValidationError("Validation issue to be caught by parent")
    except errors.NotFoundError:
        pytest.fail("Caught NotFoundError when DomainError parent was expected")
    except errors.DomainError:
        pass # Expected, as ValidationError is a DomainError
    except errors.NarratixError:
        pytest.fail("Caught NarratixError directly when DomainError parent was expected")
    except Exception:
        pytest.fail("Caught generic Exception")

    try:
        raise errors.NotFoundError("Not found issue to be caught by parent")
    except errors.DomainError:
        pytest.fail("Caught DomainError when InfrastructureError parent was expected")
    except errors.InfrastructureError:
        pass # Expected, as NotFoundError is an InfrastructureError
    except errors.NarratixError:
        pytest.fail("Caught NarratixError directly when InfrastructureError parent was expected")
    except Exception:
        pytest.fail("Caught generic Exception") 