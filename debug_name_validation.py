"""
Este script ayuda a depurar la validación de nombres de clientes.
"""
import logging

logging.basicConfig(level=logging.INFO)

def validate_name(name):
    """Valida si un nombre contiene solo letras y espacios."""
    logging.info(f"Validando nombre: '{name}'")
    
    # Verificar si contiene solo letras y espacios
    if not all(c.isalpha() or c.isspace() for c in name):
        logging.info(f"FALLO: El nombre contiene caracteres no permitidos.")
        return False
    
    # Verificar que tenga al menos una letra
    if not any(c.isalpha() for c in name):
        logging.info(f"FALLO: El nombre no contiene ninguna letra.")
        return False
    
    logging.info(f"ÉXITO: El nombre es válido.")
    return True

# Probar con un nombre con espacios
print("Probando con 'لجين محمد موسى':")
print(f"¿Es válido? {validate_name('لجين محمد موسى')}")

# Probar el funcionamiento de la condición para letras en árabe con isalpha()
name = "لجين محمد موسى"
for char in name:
    print(f"Caracter: '{char}', ¿Es alfabético? {char.isalpha()}")