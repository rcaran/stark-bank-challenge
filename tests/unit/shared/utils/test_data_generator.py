from src.shared.utils.data_generator import DataGenerator
from src.shared.utils.validators import validate_cpf, validate_cnpj

def test_data_generator_valid_cpf():
    generator = DataGenerator()
    cpf = generator.generate_valid_cpf()
    assert validate_cpf(cpf) is True

def test_data_generator_valid_cnpj():
    generator = DataGenerator()
    cnpj = generator.generate_valid_cnpj()
    assert validate_cnpj(cnpj) is True

def test_generate_person_data():
    generator = DataGenerator()
    person = generator.generate_person_data()
    assert person["type"] == "individual"
    assert "name" in person
    assert "email" in person
    assert validate_cpf(person["tax_id"]) is True

def test_generate_company_data():
    generator = DataGenerator()
    company = generator.generate_company_data()
    assert company["type"] == "company"
    assert "name" in company
    assert "email" in company
    assert validate_cnpj(company["tax_id"]) is True

def test_generate_customer_data_distribution():
    # Only verify logic works, not exact distribution
    generator = DataGenerator()
    count_person = 0
    count_company = 0
    
    # Run a few times
    for _ in range(100):
        data = generator.generate_customer_data(prefer_cpf=True)
        if data["type"] == "individual":
            count_person += 1
        else:
            count_company += 1
            
    assert count_person > 0
    assert count_company > 0
