import os
import shutil
import io
import pickle
import telegram
from re import search as re_search
from urllib.parse import parse_qs, urlparse
from os import makedirs, path as ospath, listdir, remove as osremove
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload


# =================================================================
#    G Drive Functions
# =================================================================


# extract the file ID or folder ID from the link
def __getIdFromUrl(link: str):
    if "folders" in link or "file" in link:
        regex = r"https:\/\/drive\.google\.com\/(?:drive(.*?)\/folders\/|file(.*?)?\/d\/)([-\w]+)"
        res = re_search(regex, link)
        if res is None:
            raise IndexError("G-Drive ID not found.")
        return res.group(3)
    parsed = urlparse(link)
    return parse_qs(parsed.query)["id"][0]


def __getFilesByFolderId(folder_id):
    page_token = None
    files = []
    while True:
        response = (
            service.files()
            .list(
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                q=f"'{folder_id}' in parents and trashed = false",
                spaces="drive",
                pageSize=200,
                fields="nextPageToken, files(id, name, mimeType, size, shortcutDetails)",
                orderBy="folder, name",
                pageToken=page_token,
            )
            .execute()
        )
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if page_token is None:
            break
    return files


def __getFileMetadata(file_id):
    return (
        service.files()
        .get(fileId=file_id, supportsAllDrives=True, fields="name, id, mimeType, size")
        .execute()
    )


def __download_file(file_id, path):
    # Check if the specified file or folder exists and is downloadable.
    try:
        file = service.files().get(fileId=file_id, supportsAllDrives=True).execute()
    except HttpError as error:
        print("An error occurred: {0}".format(error))
        file = None
    if file is None:
        print(
            "Sorry, the specified file or folder does not exist or is not accessible."
        )
    else:
        if file["mimeType"].startswith("application/vnd.google-apps"):
            print(
                "Sorry, the specified ID is for a Google Docs, Sheets, Slides, or Forms document. You can only download these types of files in specific formats."
            )
        else:
            # Create a BytesIO stream to hold the downloaded file data.
            file_contents = io.BytesIO()

            # Download the file or folder contents to the BytesIO stream.
            request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
            file_downloader = MediaIoBaseDownload(file_contents, request)
            done = False
            while done is False:
                status, done = file_downloader.next_chunk()
                # print(f"\rDownload progress: {int(status.progress() * 100)}%")
            file_contents.seek(0)

            # Save the downloaded file or folder to disk using its original name (if available).
            file_name = file.get("name", f"untitleddrivefile_{file_id}")
            file_name = os.path.join(path, file_name)
            with open(file_name, "wb") as handle:
                handle.write(file_contents.getbuffer())
            print(f'\nThe file "{file_name}" downloaded!')


# Usage example
# __download_file('1XQyVFHC44zso-HM2-EyLm8YeusxcqNOX', '/content/Downloads')


def __download_folder(folder_id, path):

    folder_meta = __getFileMetadata(folder_id)
    folder_name = folder_meta["name"]
    if not ospath.exists(f"{path}/{folder_name}"):
        makedirs(f"{path}/{folder_name}")
    path += f"/{folder_name}"
    result = __getFilesByFolderId(folder_id)
    if len(result) == 0:
        return
    result = sorted(result, key=lambda k: k["name"])
    for item in result:
        file_id = item["id"]
        shortcut_details = item.get("shortcutDetails")
        if shortcut_details is not None:
            file_id = shortcut_details["targetId"]
            mime_type = shortcut_details["targetMimeType"]
        else:
            mime_type = item.get("mimeType")
        if mime_type == "application/vnd.google-apps.folder":
            __download_folder(file_id, path)
        else:
            __download_file(file_id, path)


# =================================================================
#    Telegram Upload Functions
# =================================================================


def get_file_type(file_path):
    name, extension = os.path.splitext(file_path)
    if extension in [".mp4", ".avi", ".mkv", ".mov", ".webm", ".m4v"]:
        video_extension_fixer(file_path)
        return "video"
    elif extension in [".mp3", ".wav", ".flac", ".aac", ".ogg"]:
        return "audio"
    elif extension in [".jpg", ".jpeg", ".png", ".gif"]:
        return "photo"
    else:
        return "document"


def video_extension_fixer(file_path):

    dir_path, filename = os.path.split(file_path)

    if filename.endswith(".mp4") or filename.endswith(".mkv"):
        pass
    # split the file name and the extension
    else:
        # rename the video file with .mp4 extension
        name, ext = os.path.splitext(filename)
        os.rename(
            os.path.join(dir_path, filename), os.path.join(dir_path, name + ".mp4")
        )
        print(f"{filename} was changed to {name}.mp4")


def create_zip(folder_path):
    folder_name = os.path.basename(folder_path)  # get folder name from folder path
    zip_file_path = folder_path  # create zip file path
    shutil.make_archive(
        zip_file_path, "zip", folder_path
    )  # create zip file by archiving the folder
    return zip_file_path + ".zip"  # return zip file path


def size_checker(file_path):

    max_size = 2097152000  # 2 GB
    file_size = os.stat(file_path).st_size

    if file_size > max_size:

        if not ospath.exists(d_fol_path):
            makedirs(d_fol_path)

        split_zipFile(file_path, max_size)

        return True
    else:
        return False


def split_zipFile(file_path, max_size):

    dir_path, filename = os.path.split(file_path)

    new_path = f"{d_fol_path}/{filename}"

    with open(file_path, "rb") as f:
        chunk = f.read(max_size)
        i = 1

        while chunk:
            # Generate filename for this chunk
            ext = str(i).zfill(3)
            output_filename = "{}.{}".format(new_path, ext)

            # Write chunk to file
            with open(output_filename, "wb") as out:
                out.write(chunk)

            # Get next chunk
            chunk = f.read(max_size)

            # Increment chunk counter
            i += 1


async def upload_file(file_path, type, file_name):

    # Upload the file
    try:

        if type == "video":

            sent = await bot.send_video(
                chat_id=chat_id,
                video=file_path,
                supports_streaming=True,
                width=480,
                height=320,
                caption=file_name,
                thumb=thumb_path,
            )

        elif type == "audio":

            sent = await bot.send_audio(
                chat_id=chat_id,
                audio=file_path,
                supports_streaming=True,
                caption=file_name,
                thumb=thumb_path,
            )

        elif type == "document":

            sent = await bot.send_document(
                chat_id=chat_id,
                document=file_path,
                caption=file_name,
                thumb=thumb_path,
            )

        elif type == "photo":

            sent = await bot.send_photo(
                chat_id=chat_id,
                photo=file_path,
                caption=file_name,
            )

        print(f"\n{file_name} Sent !")
        print(f"LOG: {sent}")

    except Exception as e:
        print(e)


# ****************************************************************
#    Main Functions, function calls and variable declarations
# ****************************************************************


# Replace YOUR_TOKEN with your actual bot token
token = "5558586331:AAHcUlXjsECwp8UkreX7KgqelH0X_oXfTjc"

# Replace CHAT_ID with the chat ID of the recipient
chat_id = "-1001578391154"

# Replace FILE_PATH with the path to your media file
d_path = "/content/Downloads"

if not ospath.exists(d_path):
    makedirs(d_path)

# Replace THUMB_PATH with the path to your thumbnail file (optional)
thumb_path = "/content/thmb.jpg"

# Create a new Telegram bot instance using the bot token
bot = telegram.Bot(token=token)

# create credentials object from token.pickle file
creds = None
if os.path.exists("/content/token.pickle"):
    with open("/content/token.pickle", "rb") as token:
        creds = pickle.load(token)
else:
    exit(1)

# create drive API client
service = build("drive", "v3", credentials=creds)

# enter the link for the file or folder that you want to download
link = input("Enter the Google Drive link for the file or folder: ")

file_id = __getIdFromUrl(link)

meta = __getFileMetadata(file_id)

d_name = meta["name"]

d_fol_path = f"{d_path}/{d_name}"

# Determine if the ID is of file or folder
if meta.get("mimeType") == "application/vnd.google-apps.folder":
    __download_folder(file_id, d_path)
else:
    if not ospath.exists(d_fol_path):
        makedirs(d_fol_path)
    __download_file(file_id, d_fol_path)

z_file_path = create_zip(d_fol_path)

shutil.rmtree(d_fol_path)

leech = size_checker(z_file_path)

if leech: # File was splitted

    if ospath.exists(z_file_path):
      os.remove(z_file_path) # Delete original Big Zip file
    print('Big Zip File Deleted !')
    print('\n\n Now uploading multiple splitted zip files.............')

    dir_list = os.listdir(d_fol_path)

    for dir_path in dir_list:

        short_path = os.path.join(d_fol_path,dir_path)
        file_type = get_file_type(short_path)
        file_name = os.path.basename(short_path)
        # print(dir_path)
        await upload_file(short_path,file_type,file_name)

else:

    print('\nNow uploading the zip file..........................')

    file_type = get_file_type(z_file_path)
    file_name = os.path.basename(z_file_path)
    await upload_file(z_file_path,file_type,file_name)
