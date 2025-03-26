from PIL import Image
import os

def load_and_resize(image_path, scale=5):
    """Load an image and resize it by the given scale."""
    img = Image.open(image_path)
    return img.resize((img.width * scale, img.height * scale), Image.NEAREST)

# Define file paths
sample_folder = "sample"
output_folder = "map"
os.makedirs(output_folder, exist_ok=True)

ground = load_and_resize(os.path.join(sample_folder, "ground.png"))
wall = load_and_resize(os.path.join(sample_folder, "wall 5h.png"))
grass = load_and_resize(os.path.join(sample_folder, "grass.png"))
start = load_and_resize(os.path.join(sample_folder, "start.png"))

# Map dimensions
grid_width = 12
grid_height = 9
tile_size = ground.width  # Since all tiles are resized to the same size

total_width = grid_width * tile_size
total_height = grid_height * tile_size

# Create blank map
map_image = Image.new("RGBA", (total_width, total_height))

# Define map elements
grass_positions = {("C",1), ("C",2), ("D",1), ("D",2), ("E",1), ("E",2),
                    ("H",1), ("H",2), ("I",1), ("I",2), ("J",1), ("J",2),
                    ("E",8), ("F",8), ("G",8), ("H",8), ("E",9), ("F",9), ("G",9), ("H",9)}
wall_positions = {("D",4), ("D",5), ("D",6), ("D",7), ("D",8), ("D",9),
                  ("I",4), ("I",5), ("I",6), ("I",7), ("I",8), ("I",9)}
start_positions = {("B",5), ("K",5)}

# Helper function to get grid position
def get_position(letter, number):
    x = (ord(letter) - ord('A')) * tile_size
    y = (number - 1) * tile_size
    return x, y

# Fill the map
for col in range(grid_width):
    for row in range(grid_height):
        letter = chr(ord('A') + col)
        number = row + 1
        pos = get_position(letter, number)

        if (letter, number) in grass_positions:
            map_image.paste(grass, pos, grass)
        elif (letter, number) in wall_positions:
            map_image.paste(wall, pos, wall)
        elif (letter, number) in start_positions:
            map_image.paste(start, pos, start)
        else:
            map_image.paste(ground, pos, ground)

# Save the generated map
output_path = os.path.join(output_folder, "map.png")
map_image.save(output_path)
print(f"Map generated and saved as {output_path}")
