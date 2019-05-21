import io
import queue
import random
import select
import socket
import struct
import threading
import tkinter as tk
import urllib.request

from PIL import Image, ImageTk


PORT = 2525
TRANSPARENT_COLOR = '#0f0f0f'
TEXT_COLOR = '#ffffff'
TEXT_BORDER_COLOR = '#000000'
FONT_SIZE = 26
NUM_MAX_COMMENTS_IN_DISPLAY = 5
REMAINING_MILLISECONDS = 5000
FPS = 60
INTERVAL = int(1000 / FPS)
SEPARATER = '##SEP##'

running = True


class Comment(object):
    def __init__(self, canvas, text):
        self._canvas = canvas
        self._bordered_text = []
        self._icon = None
        self._img = None
        self._step_x = 0
        self.removed = False

        icon_url = None
        if text.find(SEPARATER) != -1 and text.startswith(('http://', 'https://')):
            icon_url, text = text.split(SEPARATER, 1)

        self._create_bordered_text(text)
        if icon_url:
            self._create_icon(icon_url)

    def _surrogate(self, string):
        return ''.join(c if c <= '\uffff' else ''.join(
                       chr(x) for x in struct.unpack('>2H', c.encode('utf-16be'))) for c in string)

    def _create_bordered_text(self, text):
        text = self._surrogate(text)
        x0 = self._canvas.width
        y0 = 0.95 * random.random() * self._canvas.height

        for x, y in [(x, y) for x in range(-1, 2) for y in range(-1, 2) if x != 0 or y != 0]:
            self._bordered_text.append(self._canvas.create_text((x0 + x, y0 + y),
                                       text=text, anchor='nw', fill=TEXT_BORDER_COLOR,
                                       font=('', FONT_SIZE, 'bold')))
        self._bordered_text.append(self._canvas.create_text((x0, y0), text=text, anchor='nw',
                                   fill=TEXT_COLOR, font=('', FONT_SIZE, 'bold')))

        bbox = self._canvas.bbox(self._bordered_text[-1])
        text_width = bbox[2] - bbox[0]
        self._step_x = -(self._canvas.width + text_width) / (REMAINING_MILLISECONDS / INTERVAL)

    def _create_icon(self, icon_url):
        bbox = self._canvas.bbox(self._bordered_text[-1])
        text_width = bbox[2] - bbox[0]
        icon_height = bbox[3] - bbox[1]

        req = urllib.request.urlopen(icon_url)
        pil_img = Image.open(io.BytesIO(req.read()))
        orig_width, orig_height = pil_img.size
        icon_width = orig_width * icon_height // orig_height
        pil_img = pil_img.resize((icon_width, icon_height))
        self._img = ImageTk.PhotoImage(pil_img)

        icon_x = bbox[0] + icon_width // 2
        icon_y = bbox[1] + icon_height // 2
        shift = icon_width * 5 // 4
        self._icon = self._canvas.create_image(icon_x, icon_y, image=self._img)
        for text in self._bordered_text:
            self._canvas.move(text, shift, 0)

        self._step_x -= shift / (REMAINING_MILLISECONDS / INTERVAL)

    def _remove(self):
        for text in self._bordered_text:
            self._canvas.delete(text)
        if self._icon:
            self._canvas.delete(self._icon)
        self.removed = True

    def update(self):
        for text in self._bordered_text:
            self._canvas.move(text, self._step_x, 0)
        if self._icon:
            self._canvas.move(self._icon, self._step_x, 0)
        if self._canvas.bbox(self._bordered_text[0])[2] < 0:
            self._remove()


class CommentCanvas(tk.Canvas):
    def __init__(self, width, height, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.width = width
        self.height = height
        self._comment_queue = queue.Queue()
        self._comments = []

    def add_comment(self, comment):
        self._comment_queue.put(comment)

    def _consume_comment(self):
        if len(self._comments) < NUM_MAX_COMMENTS_IN_DISPLAY:
            try:
                text = self._comment_queue.get(block=False)
                self._comments.append(Comment(self, text))
            except queue.Empty:
                pass

    def update(self):
        self._consume_comment()
        for comment in self._comments:
            comment.update()
            if comment.removed:
                self._comments.remove(comment)


def recieve_comments(canvas):
    global running
    server_sock = socket.socket()
    server_sock.bind(('', PORT))
    server_sock.listen(3)

    while running:
        ready, _, _ = select.select([server_sock], [], [], 1)
        if ready:
            s, addr = ready[0].accept()
            comment = s.recv(1024 * 10).decode().strip()
            s.close()
            print(comment)
            canvas.add_comment(comment)

    server_sock.close()


def task(root, canvas):
    canvas.update()
    root.after(INTERVAL, task, root, canvas)


def main():
    global running

    root = tk.Tk()
    root.title('comment')
    root.wm_attributes('-transparentcolor', TRANSPARENT_COLOR)
    root.config(bg=TRANSPARENT_COLOR)
    root.wm_attributes('-fullscreen', True)
    root.wm_attributes('-topmost', True)
    root.update()

    canvas = CommentCanvas(root.winfo_width(), root.winfo_height(), root,
                           bg=TRANSPARENT_COLOR, bd=0, highlightthickness=0)
    canvas.pack(expand=1, fill=tk.BOTH)

    recieve_thread = threading.Thread(target=recieve_comments, args=(canvas,))
    recieve_thread.start()
    root.after(INTERVAL, task, root, canvas)
    root.mainloop()
    running = False


if __name__ == '__main__':
    main()
