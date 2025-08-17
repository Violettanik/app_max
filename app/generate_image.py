import time
import random
from PIL import Image

def generate_user_image(output_path="user_image.png"):
    # Получаем текущее время в секундах от эпохи (1970 год, но вы можете вычесть разницу до 1990)
    current_time = int(time.time())
    
    # Создаем новое изображение 8x8 (64 блока) с стандартным размером (например, 512x512)
    width, height = 512, 512
    block_size = width // 8
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    
    # Фиксируем время вызова функции (оно не будет меняться в течение выполнения)
    fixed_time = current_time
    
    # Генерируем 64 блока
    for i in range(8):
        for j in range(8):
            # Генерируем R, G, B компоненты
            r = (fixed_time + random.randint(1, 1000000)) % 256
            g = (fixed_time + random.randint(1, 1000000)) % 256
            b = (fixed_time + random.randint(1, 1000000)) % 256
            
            # Закрашиваем блок
            for x in range(i * block_size, (i + 1) * block_size):
                for y in range(j * block_size, (j + 1) * block_size):
                    pixels[x, y] = (r, g, b)
    
    # Сохраняем изображение
    image.save(output_path)
    print(f"Изображение сохранено как {output_path}")

# Пример использования
#generate_user_image()
