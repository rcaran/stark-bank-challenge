import re

from validate_docbr import CNPJ, CPF


class Validator:
    MAX_CPF_LENGTH = 14
    MAX_CNPJ_LENGTH = 18

validator_cpf = CPF()
validator_cnpj = CNPJ()

def clean_tax_id(tax_id: str) -> str:
    """Removes non-numeric characters from a tax ID."""
    if not tax_id:
        return ""
    return re.sub(r"[^0-9]", "", str(tax_id))

def validate_cpf(cpf: str) -> bool:
    """Validates a CPF number."""
    if not cpf:
        return False
    # Validate format if punctuation is present
    if not re.match(r"^\d{3}\.\d{3}\.\d{3}-\d{2}$|^\d{11}$", str(cpf)):
        return False
    return validator_cpf.validate(cpf)

def validate_cnpj(cnpj: str) -> bool:
    """Validates a CNPJ number."""
    if not cnpj:
        return False
    # Validate format if punctuation is present
    if not re.match(r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$|^\d{14}$", str(cnpj)):
        return False
    return validator_cnpj.validate(cnpj)

def validate_tax_id(tax_id: str) -> bool:
    """Detects and validates a tax ID (CPF or CNPJ)."""
    clean_id = clean_tax_id(tax_id)
    if len(clean_id) == 11:
        return validator_cpf.validate(clean_id)
    if len(clean_id) == 14:
        return validator_cnpj.validate(clean_id)
    return False

def format_cpf(cpf: str) -> str:
    """Formats a CPF number with punctuation."""
    clean_cpf = clean_tax_id(cpf)
    if len(clean_cpf) != 11:
        raise ValueError("Invalid CPF length")
    return validator_cpf.mask(clean_cpf)

def format_cnpj(cnpj: str) -> str:
    """Formats a CNPJ number with punctuation."""
    clean_cnpj = clean_tax_id(cnpj)
    if len(clean_cnpj) != 14:
        raise ValueError("Invalid CNPJ length")
    return validator_cnpj.mask(clean_cnpj)
