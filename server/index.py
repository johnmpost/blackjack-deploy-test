import asyncio
import json
from websockets.server import serve
import tensorflow as tf
from PIL import Image
import io
import numpy as np
from image_processing import player_image_to_index_img_stacks

model = tf.keras.models.load_model('trained_model.keras')
model.summary()

with open('label_mapping.json', 'r') as file:
    index_to_label = json.load(file)

def expand_card_code(card_code):
    codes = {
        'AH': {'suit': "hearts", 'rank': "ace"},
        '2H': {'suit': "hearts", 'rank': "2"},
        '3H': {'suit': "hearts", 'rank': "3"},
        '4H': {'suit': "hearts", 'rank': "4"},
        '5H': {'suit': "hearts", 'rank': "5"},
        '6H': {'suit': "hearts", 'rank': "6"},
        '7H': {'suit': "hearts", 'rank': "7"},
        '8H': {'suit': "hearts", 'rank': "8"},
        '9H': {'suit': "hearts", 'rank': "9"},
        '10H': {'suit': "hearts", 'rank': "10"},
        'JH': {'suit': "hearts", 'rank': "jack"},
        'QH': {'suit': "hearts", 'rank': "queen"},
        'KH': {'suit': "hearts", 'rank': "king"},
        'AD': {'suit': "diamonds", 'rank': "ace"},
        '2D': {'suit': "diamonds", 'rank': "2"},
        '3D': {'suit': "diamonds", 'rank': "3"},
        '4D': {'suit': "diamonds", 'rank': "4"},
        '5D': {'suit': "diamonds", 'rank': "5"},
        '6D': {'suit': "diamonds", 'rank': "6"},
        '7D': {'suit': "diamonds", 'rank': "7"},
        '8D': {'suit': "diamonds", 'rank': "8"},
        '9D': {'suit': "diamonds", 'rank': "9"},
        '10D': {'suit': "diamonds", 'rank': "10"},
        'JD': {'suit': "diamonds", 'rank': "jack"},
        'QD': {'suit': "diamonds", 'rank': "queen"},
        'KD': {'suit': "diamonds", 'rank': "king"},
        'AC': {'suit': "clubs", 'rank': "ace"},
        '2C': {'suit': "clubs", 'rank': "2"},
        '3C': {'suit': "clubs", 'rank': "3"},
        '4C': {'suit': "clubs", 'rank': "4"},
        '5C': {'suit': "clubs", 'rank': "5"},
        '6C': {'suit': "clubs", 'rank': "6"},
        '7C': {'suit': "clubs", 'rank': "7"},
        '8C': {'suit': "clubs", 'rank': "8"},
        '9C': {'suit': "clubs", 'rank': "9"},
        '10C': {'suit': "clubs", 'rank': "10"},
        'JC': {'suit': "clubs", 'rank': "jack"},
        'QC': {'suit': "clubs", 'rank': "queen"},
        'KC': {'suit': "clubs", 'rank': "king"},
        'AS': {'suit': "spades", 'rank': "ace"},
        '2S': {'suit': "spades", 'rank': "2"},
        '3S': {'suit': "spades", 'rank': "3"},
        '4S': {'suit': "spades", 'rank': "4"},
        '5S': {'suit': "spades", 'rank': "5"},
        '6S': {'suit': "spades", 'rank': "6"},
        '7S': {'suit': "spades", 'rank': "7"},
        '8S': {'suit': "spades", 'rank': "8"},
        '9S': {'suit': "spades", 'rank': "9"},
        '10S': {'suit': "spades", 'rank': "10"},
        'JS': {'suit': "spades", 'rank': "jack"},
        'QS': {'suit': "spades", 'rank': "queen"},
        'KS': {'suit': "spades", 'rank': "king"}
        }
    return codes[card_code]


def preprocess_image_for_inference(img_array):
    THRESHOLD = -15
    grey_img = np.mean(img_array, axis=2) # Take the average across the RGB channels
    threshold = np.median(grey_img) + THRESHOLD
    binarized_img = np.where(grey_img > threshold, 1, 0) # Above median = 1 (white), else 0 (black)
    binarized_img_stacked = np.stack([binarized_img]*3, axis=-1)
    return binarized_img_stacked

def infer_card_code_from_index(img_array):
    preprocessed_img_array = preprocess_image_for_inference(img_array)
    softmax, *rest = model.predict(np.expand_dims(preprocessed_img_array, axis=0))
    predicted_label_index = np.argmax(softmax)
    predicted_card_code = index_to_label[str(predicted_label_index)]
    return predicted_card_code

# returns a list of stacks
def infer_player(image_bytes):
    index_img_stacks = player_image_to_index_img_stacks(image_bytes)
    inferred_stacks = [[expand_card_code(infer_card_code_from_index(img)) for img in img_stack] for img_stack in index_img_stacks]
    return inferred_stacks

# returns a full table record
def infer_frame(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))

    width, height = img.size

    dealer = (0, 0, width, height//2)
    p1 = (0, height//2, width//3, height)
    p2 = (width//3, height//2, width//3*2, height)
    p3 = (width//3*2, height//2, width, height)

    dealer_img = img.crop(dealer)
    p1_img = img.crop(p1)
    p2_img = img.crop(p2)
    p3_img = img.crop(p3)

    # list of stacks, stack is list of cards
    dealer_stacks = infer_player(dealer_img)
    p1_stacks = infer_player(p1_img)
    p2_stacks = infer_player(p2_img)
    p3_stacks = infer_player(p3_img)

    result = {
        "dealer": dealer_stacks,
        "player1": p1_stacks,
        "player2": p2_stacks,
        "player3": p3_stacks
    }
    return result

async def get_data(websocket):
    async for message in websocket:
        await websocket.send(json.dumps(infer_frame(message)))

async def main():
    async with serve(get_data, "0.0.0.0", 4444):
        await asyncio.Future()

with open("./test-table.jpg", "rb") as file:
    img_bytes = file.read()

print(infer_frame(img_bytes))

print("starting server")
asyncio.run(main())
