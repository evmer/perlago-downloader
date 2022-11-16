from io import BytesIO
from PIL import Image
import asyncio
import shutil
import base64
import time
import json
import re
import os

import requests
import websocket
from pyppeteer import launch
from PyPDF2 import PdfMerger

BOOK_ID = "#BOOK_ID#"
AUTH_TOKEN = "#from io import BytesIO
from PIL import Image
import asyncio
import shutil
import base64
import time
import json
import re
import os

import requests
import websocket
from pyppeteer import launch
from PyPDF2 import PdfMerger

BOOK_ID = "#1558726#"
AUTH_TOKEN = "#Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxNzU2OTI2LCJ0b2tlbiI6IjJkMmYzMTlhLTI0MzMtNDA2Yy1hMmQxLTc4YmY1NWRlMGFmMCIsInBlcnNpc3RlbnQiOiJ0cnVlIiwiaWF0IjoxNjY3ODEwMjQ5fQ.FoE8hG5HzcSzqZ9aHwCegcrCAprR93c8BjDQ4jLHVvFiAB3_05FLjf8a6FR6F3kjhulZkc7URIKwmpfSIXgUL9LU_MJDGGvmzVqb1bu5qnUNheKZ7rQm9jbVACYFfbCT-NL2k24KOQhWYGu7mx4tePvZzpYLVUBUKMLgXl9d_q9_XAu20IyS_6ASvQyKCMZUDFDwwxGw4_FJmzwYvkToMsxlOuoW1nbKs8CKoaMnaRpjb6d62sLaOUEwlOq4GpB7ANDGysp9THL2x_w0_Yakd_qMP4ac71zHF1_QV0QcErgwc8mtpmi34pb-Nnz-EtGdZMKAevQ4lYIyiAA977rI-qoGsjh4hs090kqup_OZ9q7xzPKdSO2wRih03raZ5UK2PX7KCd1EKlLDODGo_N5rchSGGNHaOM8S-FirQt20ZCDgwsYlJPk1lY5x1jydkkYj8JHhmsN1pJeK79sD3eMk5ZRpig7ykx9eZGstnSyMQRuqs0b4VyK0B46oQWXT9lEWRHcn-QT_k8FRmn1QzHS0Itgjo2PIMxEg1yO9lR85yXBKb19yr_tVTAoUwgDIHtQak6SXl9jo1n5o0JvnEPQq-dsoh13b5C8gRUczjaukdsHjNI-JztScAQRkGVxognJvMTIUPnr0WSi-ymw_Qq500b8WNXgCqqhuPp4-X2x9nfc#"

PUPPETEER_THREADS = 50

def init_book_delivery():
	while True:
		try:
			ws = websocket.create_connection("wss://api-ws.perlego.com/book-delivery/", skip_utf8_validation=True, timeout=30)
		except Exception as error:
			print(f'init_book_delivery() error: {error}')
			continue
		break

	time.sleep(1)

	ws.send(json.dumps({"action":"initialise","data":{"authToken": AUTH_TOKEN, "reCaptchaToken": AUTH_TOKEN, "bookId": str(BOOK_ID)}}))

	return ws

class merged_chapter:
	def __init__(self):
		self.merged_chapter_number = 1

class chapter:
	def __init__(self):
		self.page_id = 1

		self.contents = {}


# download pages content
while True:

	chapters = {}
	contents = {}
	page_id = None

	ws = init_book_delivery()

	init_data = {}

	while True:
		try:
			data = json.loads(ws.recv())
		except Exception as error:
			print(f'download error: {error}')
			ws = init_book_delivery()
			continue

		if data['event'] == 'initialisationDataChunk':
			if page_id != None: # we're here because ws conn broke, so we can resume from last page_id
				ws.send(json.dumps({"action":"loadPage","data":{"authToken": AUTH_TOKEN, "pageId": page_id, "bookType": book_format, "windowWidth":1792, "mergedChapterPartIndex":0}}))
				merged_chapter_part_idx = 0
				# reset latest content
				contents[page_id] = {}
				for i in chapters[page_id]: contents[i] = {}
				continue

			chunk_no = data['data']['chunkNumber']
			init_data[chunk_no] = data['data']['content']

			# download all the chunks before proceeding
			if len(init_data) != data['data']['numberOfChunks']: continue

			# merge the initialisation content
			data_content = ""
			for chunk_no in sorted(init_data):
				data_content += init_data[chunk_no]

			# extract the relevant data
			data_content = json.loads(json.loads(data_content))
			book_format = data_content['bookType']
			merged_chapter_part_idx = 0

			if book_format == 'EPUB':
				bookmap = data_content['bookMap']
				for chapter_no in bookmap:
					chapters[int(chapter_no)] = []
					contents[int(chapter_no)] = {}
					for subchapter_no in bookmap[chapter_no]:
						chapters[int(chapter_no)].append(subchapter_no)
						contents[subchapter_no] = {}
			elif book_format == 'PDF':
				for i in range(1, data_content['numberOfChapters'] + 1):
					chapters[i] = []
					contents[i] = {}
			else:
				raise Exception(f'unknown book format ({book_format})!')

			ws.send(json.dumps({"action":"loadPage","data":{"authToken": AUTH_TOKEN, "pageId": list(chapters)[0], "bookType": book_format, "windowWidth":1792, "mergedChapterPartIndex":0}}))


		elif 'pageChunk' in data['event']:
			page_id = int(data['data']['pageId'])

			merged_chapter_no = (int(data['data']['mergedChapterNumber']) - 1) if book_format == 'EPUB' else 0
			number_of_merged_chapters = int(data['data']['numberOfMergedChapters']) if book_format == 'EPUB' else 1

			chunk_no = int(data['data']['chunkNumber']) - 1
			number_of_chunks = int(data['data']['numberOfChunks'])

			chapter_no = page_id + merged_chapter_no + merged_chapter_part_idx

			if contents.get(chapter_no) == None:
				contents[chapter_no] = {}
				chapters[page_id].append(chapter_no)

			if contents[chapter_no] == {}:
				for i in range(number_of_chunks):
					contents[chapter_no][i] = ""

			contents[chapter_no][chunk_no] = data['data']['content']

			# check if all merged chapters have been downloaded
			if not all(contents.get(i) not in [None, {}] for i in range(page_id, page_id+number_of_merged_chapters+merged_chapter_part_idx)): continue

			# check if all chunks of all merged pages/chapters have been downloaded
			if not all( all(chunk != "" for chunk in contents[i].values() ) for i in range(page_id, page_id+number_of_merged_chapters+merged_chapter_part_idx)): continue

			# check if all pages/chapters have been downloaded
			if all(contents[i] != {} for i in [page_id]+chapters[page_id]):

				print(f"{'chapters' if book_format == 'EPUB' else 'page'} {page_id}-{page_id+number_of_merged_chapters+merged_chapter_part_idx} downloaded")
				merged_chapter_part_idx = 0
				try:
					next_page = list(chapters)[list(chapters).index(page_id) + 1]
				except IndexError:
					break
			else:
				merged_chapter_part_idx += 1
				next_page = page_id

			ws.send(json.dumps({"action":"loadPage","data":{"authToken": AUTH_TOKEN, "pageId": str(next_page), "bookType": book_format, "windowWidth":1792, "mergedChapterPartIndex":merged_chapter_part_idx}}))

	break

# create cache dir
cache_dir = f'{os.getcwd()}/{book_format}_{BOOK_ID}/'
try:
	os.mkdir(cache_dir)
except FileExistsError:
	pass

# convert html files to pdf
async def html2pdf():

	# start headless chrome
	browser = await launch(options={
			'headless': True,
			'autoClose': False,
			'args': [
				'--no-sandbox',
				'--disable-setuid-sandbox',
				'--disable-dev-shm-usage',
				'--disable-accelerated-2d-canvas',
				'--no-first-run',
				'--no-zygote',
				'--single-process',
				'--disable-gpu',
				'--disable-web-security',
				'--webkit-print-color-adjust',
				'--disable-extensions'
			],
		},
	)

	async def render_page(chapter_no, semaphore):

		async with sem:

			page = await browser.newPage()
			await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36')

			# download cover separately
			if chapter_no == 0:
				r = requests.get(f"https://api.perlego.com/metadata/v2/metadata/books/{BOOK_ID}")
				cover_url = json.loads(r.text)['data']['results'][0]['cover']
				img = Image.open(BytesIO(requests.get(cover_url).content))
				img.save(f'{cache_dir}/0.pdf')
				return

			# merge chunks
			content = ""
			for chunk_no in sorted(contents[chapter_no]):
				content += contents[chapter_no][chunk_no]

			# remove useless img (mess up with pdf gen)
			if book_format == 'EPUB':
				match = re.search('<img id="trigger" data-chapterid="[0-9]*?" src="" onerror="LoadChapter\(\'[0-9]*?\'\)" />', content).group(0)
				if match: content = content.replace(match, '')

			# reveal hidden images
			imgs = re.findall("<img.*?>", content, re.S)
			for img in imgs:
				img_new = img.replace('opacity: 0', 'opacity: 1')
				img_new = img_new.replace('data-src', 'src')
				content = content.replace(img, img_new)

			# save page in the cache dir
			f = open(f'{cache_dir}/{chapter_no}.html', 'w', encoding='utf-8')
			f.write('<meta charset="utf-8" />\n')
			f.write(content)
			f.close()

			# render html
			await page.goto(f'file://{cache_dir}/{chapter_no}.html', {"waitUntil" : ["load", "domcontentloaded", "networkidle0", "networkidle2"], "timeout": 0})

			# set pdf options
			options = {'path': f'{cache_dir}/{chapter_no}.pdf'}
			if book_format == 'PDF':
				width, height = await page.evaluate("() => { return [document.documentElement.offsetWidth + 1, document.documentElement.offsetHeight + 1]}")
				options['width'] = width
				options['height'] =  height
			elif book_format == 'EPUB':
				options['margin'] = {'top': '20', 'bottom': '20', 'left': '20', 'right': '20'}
				
			# build pdf
			await page.pdf(options)

			print(f"{chapter_no}.pdf created")

	sem = asyncio.Semaphore(PUPPETEER_THREADS)
	await asyncio.gather(*[render_page(chapter_no, sem) for chapter_no in contents])

	await browser.close()

asyncio.run(html2pdf())

# merge pdfs
print('merging pdf pages...')
merger = PdfMerger()

for chapter_no in sorted(contents):
	merger.append(f'{cache_dir}/{chapter_no}.pdf')

merger.write(f"{BOOK_ID}.pdf")
merger.close()

# delete cache dir
shutil.rmtree(f'{book_format}_{BOOK_ID}')#"

PUPPETEER_THREADS = 50

def init_book_delivery():
	while True:
		try:
			ws = websocket.create_connection("wss://api-ws.perlego.com/book-delivery/", skip_utf8_validation=True, timeout=30)
		except Exception as error:
			print(f'init_book_delivery() error: {error}')
			continue
		break

	time.sleep(1)

	ws.send(json.dumps({"action":"initialise","data":{"authToken": AUTH_TOKEN, "reCaptchaToken": AUTH_TOKEN, "bookId": str(BOOK_ID)}}))

	return ws

class merged_chapter:
	def __init__(self):
		self.merged_chapter_number = 1

class chapter:
	def __init__(self):
		self.page_id = 1

		self.contents = {}


# download pages content
while True:

	chapters = {}
	contents = {}
	page_id = None

	ws = init_book_delivery()

	init_data = {}

	while True:
		try:
			data = json.loads(ws.recv())
		except Exception as error:
			print(f'download error: {error}')
			ws = init_book_delivery()
			continue

		if data['event'] == 'initialisationDataChunk':
			if page_id != None: # we're here because ws conn broke, so we can resume from last page_id
				ws.send(json.dumps({"action":"loadPage","data":{"authToken": AUTH_TOKEN, "pageId": page_id, "bookType": book_format, "windowWidth":1792, "mergedChapterPartIndex":0}}))
				merged_chapter_part_idx = 0
				# reset latest content
				contents[page_id] = {}
				for i in chapters[page_id]: contents[i] = {}
				continue

			chunk_no = data['data']['chunkNumber']
			init_data[chunk_no] = data['data']['content']

			# download all the chunks before proceeding
			if len(init_data) != data['data']['numberOfChunks']: continue

			# merge the initialisation content
			data_content = ""
			for chunk_no in sorted(init_data):
				data_content += init_data[chunk_no]

			# extract the relevant data
			data_content = json.loads(json.loads(data_content))
			book_format = data_content['bookType']
			merged_chapter_part_idx = 0

			if book_format == 'EPUB':
				bookmap = data_content['bookMap']
				for chapter_no in bookmap:
					chapters[int(chapter_no)] = []
					contents[int(chapter_no)] = {}
					for subchapter_no in bookmap[chapter_no]:
						chapters[int(chapter_no)].append(subchapter_no)
						contents[subchapter_no] = {}
			elif book_format == 'PDF':
				for i in range(1, data_content['numberOfChapters'] + 1):
					chapters[i] = []
					contents[i] = {}
			else:
				raise Exception(f'unknown book format ({book_format})!')

			ws.send(json.dumps({"action":"loadPage","data":{"authToken": AUTH_TOKEN, "pageId": list(chapters)[0], "bookType": book_format, "windowWidth":1792, "mergedChapterPartIndex":0}}))


		elif 'pageChunk' in data['event']:
			page_id = int(data['data']['pageId'])

			merged_chapter_no = (int(data['data']['mergedChapterNumber']) - 1) if book_format == 'EPUB' else 0
			number_of_merged_chapters = int(data['data']['numberOfMergedChapters']) if book_format == 'EPUB' else 1

			chunk_no = int(data['data']['chunkNumber']) - 1
			number_of_chunks = int(data['data']['numberOfChunks'])

			chapter_no = page_id + merged_chapter_no + merged_chapter_part_idx

			if contents.get(chapter_no) == None:
				contents[chapter_no] = {}
				chapters[page_id].append(chapter_no)

			if contents[chapter_no] == {}:
				for i in range(number_of_chunks):
					contents[chapter_no][i] = ""

			contents[chapter_no][chunk_no] = data['data']['content']

			# check if all merged chapters have been downloaded
			if not all(contents.get(i) not in [None, {}] for i in range(page_id, page_id+number_of_merged_chapters+merged_chapter_part_idx)): continue

			# check if all chunks of all merged pages/chapters have been downloaded
			if not all( all(chunk != "" for chunk in contents[i].values() ) for i in range(page_id, page_id+number_of_merged_chapters+merged_chapter_part_idx)): continue

			# check if all pages/chapters have been downloaded
			if all(contents[i] != {} for i in [page_id]+chapters[page_id]):

				print(f"{'chapters' if book_format == 'EPUB' else 'page'} {page_id}-{page_id+number_of_merged_chapters+merged_chapter_part_idx} downloaded")
				merged_chapter_part_idx = 0
				try:
					next_page = list(chapters)[list(chapters).index(page_id) + 1]
				except IndexError:
					break
			else:
				merged_chapter_part_idx += 1
				next_page = page_id

			ws.send(json.dumps({"action":"loadPage","data":{"authToken": AUTH_TOKEN, "pageId": str(next_page), "bookType": book_format, "windowWidth":1792, "mergedChapterPartIndex":merged_chapter_part_idx}}))

	break

# create cache dir
cache_dir = f'{os.getcwd()}/{book_format}_{BOOK_ID}/'
try:
	os.mkdir(cache_dir)
except FileExistsError:
	pass

# convert html files to pdf
async def html2pdf():

	# start headless chrome
	browser = await launch(options={
			'headless': True,
			'autoClose': False,
			'args': [
				'--no-sandbox',
				'--disable-setuid-sandbox',
				'--disable-dev-shm-usage',
				'--disable-accelerated-2d-canvas',
				'--no-first-run',
				'--no-zygote',
				'--single-process',
				'--disable-gpu',
				'--disable-web-security',
				'--webkit-print-color-adjust',
				'--disable-extensions'
			],
		},
	)

	async def render_page(chapter_no, semaphore):

		async with sem:

			page = await browser.newPage()
			await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36')

			# download cover separately
			if chapter_no == 0:
				r = requests.get(f"https://api.perlego.com/metadata/v2/metadata/books/{BOOK_ID}")
				cover_url = json.loads(r.text)['data']['results'][0]['cover']
				img = Image.open(BytesIO(requests.get(cover_url).content))
				img.save(f'{cache_dir}/0.pdf')
				return

			# merge chunks
			content = ""
			for chunk_no in sorted(contents[chapter_no]):
				content += contents[chapter_no][chunk_no]

			# remove useless img (mess up with pdf gen)
			if book_format == 'EPUB':
				match = re.search('<img id="trigger" data-chapterid="[0-9]*?" src="" onerror="LoadChapter\(\'[0-9]*?\'\)" />', content).group(0)
				if match: content = content.replace(match, '')

			# reveal hidden images
			imgs = re.findall("<img.*?>", content, re.S)
			for img in imgs:
				img_new = img.replace('opacity: 0', 'opacity: 1')
				img_new = img_new.replace('data-src', 'src')
				content = content.replace(img, img_new)

			# save page in the cache dir
			f = open(f'{cache_dir}/{chapter_no}.html', 'w', encoding='utf-8')
			f.write('<meta charset="utf-8" />\n')
			f.write(content)
			f.close()

			# render html
			await page.goto(f'file://{cache_dir}/{chapter_no}.html', {"waitUntil" : ["load", "domcontentloaded", "networkidle0", "networkidle2"], "timeout": 0})

			# set pdf options
			options = {'path': f'{cache_dir}/{chapter_no}.pdf'}
			if book_format == 'PDF':
				width, height = await page.evaluate("() => { return [document.documentElement.offsetWidth + 1, document.documentElement.offsetHeight + 1]}")
				options['width'] = width
				options['height'] =  height
			elif book_format == 'EPUB':
				options['margin'] = {'top': '20', 'bottom': '20', 'left': '20', 'right': '20'}
				
			# build pdf
			await page.pdf(options)

			print(f"{chapter_no}.pdf created")

	sem = asyncio.Semaphore(PUPPETEER_THREADS)
	await asyncio.gather(*[render_page(chapter_no, sem) for chapter_no in contents])

	await browser.close()

asyncio.run(html2pdf())

# merge pdfs
print('merging pdf pages...')
merger = PdfMerger()

for chapter_no in sorted(contents):
	merger.append(f'{cache_dir}/{chapter_no}.pdf')

merger.write(f"{BOOK_ID}.pdf")
merger.close()

# delete cache dir
shutil.rmtree(f'{book_format}_{BOOK_ID}')
