import asyncio
from pyrogram import Client
import os
import datetime

# replace the values with your own telegram API values obtained after creating a bot via Botfather

api_id = 14269266
api_hash = "d454cd5c47a4cea89b6ce7448c532fc4"
bot_token = "5558586331:AAHcUlXjsECwp8UkreX7KgqelH0X_oXfTjc"

async def progress(current, total):
    # Calculate upload speed only when the current number of bytes is greater than zero
    if current > 0:
        elapsed_time_seconds = (datetime.datetime.now() - start_time).seconds
        upload_speed = current / elapsed_time_seconds
        upload_speed /= 1024 
        speed_string = f"({upload_speed:.2f} KB/s)"

    print(f'Uploaded: {current / (1024 * 1024):.5f} MB  |  Total: {total/ (1024 * 1024):.5f} MB  =>  {current * 100 / total:.1f}%  {speed_string}')
    



async def send_document():
    # create a pyrogram client instance
    client = Client('my_bot', api_id = api_id, api_hash = api_hash, bot_token=bot_token)

    await client.start()

    # with open('/content/Downloads/(ISC)² CAP Fundamentals - [Telegram @Myhackersworld2 ].zip', 'rb') as f:
    #     file = f.read()

    file_path = '/content/sample_data.zip'
        
    # replace the chat_id with the id of the telegram chat where you want to send the document
    chat_id = '-1001578391154'

    # send the document to the specified chat
    try:
        await client.send_document(chat_id=int(chat_id), document=file_path, disable_notification=True, progress=progress)
        print("\nDocument sent successfully.")
    except Exception as e:
        print(f"An error occurred while sending the document: {e}")
    
    # end the client connection
    await client.stop()


start_time = datetime.datetime.now()

# run the function
# asyncio.get_event_loop().run_until_complete(send_document())
await send_document()
