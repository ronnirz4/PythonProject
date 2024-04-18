import telebot
from loguru import logger
import time
from telebot.types import InputFile
import os
from PIL import Image, ImageDraw, ImageFilter
from random import randint

class Bot:

    def __init__(self, token, telegram_chat_url):
        # create a new instance of the TeleBot class.
        # all communication with Telegram servers are done using self.telegram_bot_client
        self.telegram_bot_client = telebot.TeleBot(token)

        # remove any existing webhooks configured in Telegram servers
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)

        # set the webhook URL
        self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/', timeout=60)

        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')

    def send_text(self, chat_id, text):
        self.telegram_bot_client.send_message(chat_id, text)

    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)

    def is_current_msg_photo(self, msg):
        return 'photo' in msg

    def download_user_photo(self, msg):
        """
        Downloads the photos that sent to the Bot to `photos` directory (should be existed)
        :return: Complete file path of the downloaded photo
        """
        if not self.is_current_msg_photo(msg):
            raise RuntimeError(f'Message content of type \'photo\' expected')

        file_info = self.telegram_bot_client.get_file(msg['photo'][-1]['file_id'])
        data = self.telegram_bot_client.download_file(file_info.file_path)
        folder_name = file_info.file_path.split('/')[0]

        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        file_path = os.path.join(folder_name, file_info.file_path.split('/')[-1])

        with open(file_path, 'wb') as photo:
            photo.write(data)

        return file_path

    def send_photo(self, chat_id, img_path):
        if not os.path.exists(img_path):
            raise RuntimeError("Image path doesn't exist")

        self.telegram_bot_client.send_photo(
            chat_id,
            InputFile(img_path)
        )

    def handle_message(self, msg):
        """Bot Main message handler"""
        logger.info(f'Incoming message: {msg}')
        self.send_text(msg['chat']['id'], f'Your original message: {msg["text"]}')


class QuoteBot(Bot):
    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')

        if msg["text"] != 'Please don\'t quote me':
            self.send_text_with_quote(msg['chat']['id'], msg["text"], quoted_msg_id=msg["message_id"])


class ImageProcessingBot(Bot):
    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')

        if self.is_current_msg_photo(msg):
            try:
                caption = msg.get("caption", "").lower()
                if caption not in ['blur', 'contour', 'rotate', 'segment', 'salt and pepper', 'concat']:
                    self.send_text(msg['chat']['id'], "Unsupported filter. Supported filters are: Blur, Contour, Rotate, Segment, Salt and Pepper, Concat")
                    return

                img_path = self.download_user_photo(msg)
                if caption == 'blur':
                    processed_img = self.apply_blur_filter(img_path)
                elif caption == 'contour':
                    processed_img = self.apply_contour_filter(img_path)
                elif caption == 'rotate':
                    processed_img = self.apply_rotate_filter(img_path)
                elif caption == 'segment':
                    processed_img = self.apply_segment_filter(img_path)
                elif caption == 'salt and pepper':
                    processed_img = self.apply_salt_and_pepper_filter(img_path)
                elif caption == 'concat':
                    processed_img = self.apply_concat_filter(img_path)

                self.send_photo(msg['chat']['id'], processed_img)
                os.remove(img_path)  # Remove the downloaded image after processing
            except Exception as e:
                logger.error(f"Error processing image: {e}")
                self.send_text(msg['chat']['id'], "Error processing image. Please try again later.")
        else:
            self.send_text(msg['chat']['id'], "Please send a photo with a caption indicating the filter to apply.")

    def apply_blur_filter(self, img_path):
        """
        Apply blur filter to the image located at img_path and return the path of the processed image.
        """
        original_img = Image.open(img_path)
        processed_img = original_img.filter(ImageFilter.BLUR)
        processed_img_path = f"{img_path.split('.')[0]}_blur.jpg"
        processed_img.save(processed_img_path)
        return processed_img_path

    def apply_contour_filter(self, img_path):
        """
        Apply contour filter to the image located at img_path and return the path of the processed image.
        """
        original_img = Image.open(img_path)

        # Convert the image to grayscale
        grayscale_img = original_img.convert('L')

        # Create a new blank image with the same size and mode as the original image
        contour_img = Image.new('RGB', grayscale_img.size)

        # Create a drawing context
        draw = ImageDraw.Draw(contour_img)

        # Apply contour filter by drawing contours
        width, height = grayscale_img.size
        for x in range(1, width - 1):  # Exclude edge pixels
            for y in range(1, height - 1):  # Exclude edge pixels
                # Get the pixel value at (x, y)
                pixel = grayscale_img.getpixel((x, y))
                # Check the surrounding pixels to create a contour effect
                surrounding_pixels = [
                    grayscale_img.getpixel((x - 1, y)),
                    grayscale_img.getpixel((x + 1, y)),
                    grayscale_img.getpixel((x, y - 1)),
                    grayscale_img.getpixel((x, y + 1))
                ]
                # Calculate the average difference between the current pixel and surrounding pixels
                difference = sum(surrounding_pixels) - 4 * pixel
                # Set the pixel color in the contour image based on the difference
                draw.point((x, y), fill=(max(0, pixel - difference),) * 3)

        # Save the processed image
        processed_img_path = f"{img_path.split('.')[0]}_contour.jpg"
        contour_img.save(processed_img_path)

        return processed_img_path

    def apply_rotate_filter(self, img_path, angle=45):
        """
        Apply rotation filter to the image located at img_path and return the path of the processed image.
        """
        original_img = Image.open(img_path)
        rotated_img = original_img.rotate(angle)
        processed_img_path = f"{img_path.split('.')[0]}_rotate.jpg"
        rotated_img.save(processed_img_path)
        return processed_img_path

    def apply_segment_filter(self, img_path, threshold=128):
        """
        Apply segmentation filter to the image located at img_path and return the path of the processed image.
        """
        original_img = Image.open(img_path)
        segmented_img = original_img.point(lambda p: p > threshold and 255)
        processed_img_path = f"{img_path.split('.')[0]}_segment.jpg"
        segmented_img.save(processed_img_path)
        return processed_img_path

    def apply_salt_and_pepper_filter(self, img_path, density=0.05):
        """
        Apply salt and pepper noise filter to the image located at img_path and return the path of the processed image.
        """
        original_img = Image.open(img_path)
        width, height = original_img.size
        salt_and_pepper_img = original_img.copy()

        num_pixels = int(width * height * density)
        for _ in range(num_pixels):
            x = randint(0, width - 1)
            y = randint(0, height - 1)
            salt_or_pepper = randint(0, 1)
            if salt_or_pepper == 0:
                salt_and_pepper_img.putpixel((x, y), (0, 0, 0))  # Black pixel (salt)
            else:
                salt_and_pepper_img.putpixel((x, y), (255, 255, 255))  # White pixel (pepper)

        processed_img_path = f"{img_path.split('.')[0]}_salt_and_pepper.jpg"
        salt_and_pepper_img.save(processed_img_path)
        return processed_img_path

    def apply_concat_filter(self, img_path):
        """
        Apply concatenation filter to the image located at img_path and return the path of the processed image.
        """
        original_img = Image.open(img_path)
        width, height = original_img.size
        concat_img = Image.new('RGB', (width * 2, height))

        concat_img.paste(original_img, (0, 0))
        concat_img.paste(original_img, (width, 0))

        processed_img_path = f"{img_path.split('.')[0]}_concat.jpg"
        concat_img.save(processed_img_path)
        return processed_img_path
