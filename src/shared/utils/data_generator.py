import random
from typing import Any, Dict

from faker import Faker

from src.shared.utils.validators import validator_cnpj, validator_cpf


class DataGenerator:
    def __init__(self, locale: str = 'pt_BR'):
        self.faker = Faker(locale)
        # Seed for reproducibility if needed, but usually we want randomness
        # self.faker.seed_instance(42)

    def generate_valid_cpf(self) -> str:
        """Generates a valid, formatted CPF."""
        return validator_cpf.generate(True)

    def generate_valid_cnpj(self) -> str:
        """Generates a valid, formatted CNPJ."""
        return validator_cnpj.generate(True)

    def generate_person_data(self) -> Dict[str, Any]:
        """Generates mock data for a person (PF)."""
        return {
            "name": self.faker.name(),
            "tax_id": self.generate_valid_cpf(),
            "email": self.faker.email(),
            "type": "individual"
        }

    def generate_company_data(self) -> Dict[str, Any]:
        """Generates mock data for a company (PJ)."""
        return {
            "name": self.faker.company(),
            "tax_id": self.generate_valid_cnpj(),
            "email": self.faker.company_email(),
            "type": "company"
        }

    def generate_customer_data(self, prefer_cpf: bool = True) -> Dict[str, Any]:
        """
        Generates customer data, either PF (70% probability) or PJ (30% probability)
        if prefer_cpf is True, otherwise equal probability or customized.

        Args:
            prefer_cpf: If True, 70% chance of generating a person.
        """
        if prefer_cpf:
            is_person = random.random() < 0.7
        else:
            is_person = random.choice([True, False])

        if is_person:
            return self.generate_person_data()
        else:
            return self.generate_company_data()
