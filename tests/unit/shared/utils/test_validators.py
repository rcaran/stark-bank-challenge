import pytest
from src.shared.utils.validators import (
    validate_cpf, validate_cnpj, validate_tax_id,
    format_cpf, format_cnpj, clean_tax_id
)

# Use dummy valid CPF/CNPJ from generate_docbr or known valid ones
# For simplicity, we can rely on data_generator to produce valid ones later, or hardcode known ones.
# But validate_docbr has generate logic too.

from validate_docbr import CPF, CNPJ
cpf_gen = CPF()
cnpj_gen = CNPJ()

def test_validate_cpf():
    valid_cpf = cpf_gen.generate(True)
    assert validate_cpf(valid_cpf) is True
    
    invalid_cpf = "123.456.789-00" # bad check digit
    assert validate_cpf(invalid_cpf) is False
    
    assert validate_cpf("") is False

def test_validate_cnpj():
    valid_cnpj = cnpj_gen.generate(True)
    assert validate_cnpj(valid_cnpj) is True
    
    invalid_cnpj = "12.345.678/0001-00" # bad check digit
    assert validate_cnpj(invalid_cnpj) is False
    
    assert validate_cnpj("") is False

def test_validate_tax_id():
    valid_cpf = cpf_gen.generate(True)
    valid_cnpj = cnpj_gen.generate(True)
    
    assert validate_tax_id(valid_cpf) is True
    assert validate_tax_id(valid_cnpj) is True
    assert validate_tax_id("123") is False

def test_format_cpf():
    raw_cpf = cpf_gen.generate(False)
    formatted = format_cpf(raw_cpf)
    assert len(formatted) == 14
    assert "-" in formatted
    assert "." in formatted

    with pytest.raises(ValueError):
        format_cpf("123")

def test_format_cnpj():
    raw_cnpj = cnpj_gen.generate(False)
    formatted = format_cnpj(raw_cnpj)
    assert len(formatted) == 18
    assert "/" in formatted
    
    with pytest.raises(ValueError):
        format_cnpj("123")

def test_clean_tax_id():
    assert clean_tax_id("123.456.789-00") == "12345678900"
    assert clean_tax_id("12.345.678/0001-00") == "12345678000100"
    assert clean_tax_id(None) == ""
