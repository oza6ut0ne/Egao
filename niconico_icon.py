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
SEP = '##ICON##'

running = True


class CommentCanvas(tk.Canvas):
    def __init__(self, width, height, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._width = width
        self._height = height
        self._comment_queue = queue.Queue()
        self._texts = []

    def add_comment(self, comment):
        self._comment_queue.put(comment)

    def _add_bordered_text(self, text):
        icon_url = None
        if text.find(SEP) != -1 and text.startswith(('http://', 'https://')):
            icon_url, text = text.split(SEP, 1)

        bordered_text = []
        x0 = self._width
        y0 = 0.95 * random.random() * self._height

        for x, y in [(x, y) for x in range(-1, 2) for y in range(-1, 2) if x != 0 or y != 0]:
            bordered_text.append(self.create_text((x0 + x, y0 + y), text=text, anchor='nw',
                                fill=TEXT_BORDER_COLOR, font=('', FONT_SIZE, 'bold')))

        bordered_text.append(self.create_text((x0, y0), text=text, anchor='nw',
                             fill=TEXT_COLOR, font=('', FONT_SIZE, 'bold')))

        bbox = self.bbox(bordered_text[-1])
        text_width = bbox[2] - bbox[0]

        icon_width = 0
        img = None
        if icon_url:
            icon_height = bbox[3] - bbox[1]
            req = urllib.request.urlopen(icon_url)
            pil_img = Image.open(io.BytesIO(req.read()))
            orig_width, orig_height = pil_img.size
            icon_width = orig_width * icon_height // orig_height
            pil_img = pil_img.resize((icon_width, icon_height))
            img = ImageTk.PhotoImage(pil_img)
            tk_img = self.create_image(x0 + icon_width//2, y0 + icon_height//2, image=img)
            for text in bordered_text:
                self.move(text, icon_width*5//4, 0)
            bordered_text.append(tk_img)

        step_x = -(self._width + text_width + icon_width*5//4) / (REMAINING_MILLISECONDS / INTERVAL)
        self._texts.append((step_x, bordered_text, img))

    def _remove_text(self, bordered_text):
        for text in bordered_text:
            self.delete(text)
        self._texts.remove(bordered_text)

    def _consume_comment(self):
        if len(self._texts) < NUM_MAX_COMMENTS_IN_DISPLAY:
            try:
                comment = self._comment_queue.get(block=False)
                self._add_bordered_text(comment)
            except queue.Empty:
                pass

    def draw(self):
        self._consume_comment()
        for step_x, bordered_text, img in self._texts:
            for text in bordered_text:
                self.move(text, step_x, 0)
            if self.bbox(bordered_text[0])[2] < 0:
                self._remove_text((step_x, bordered_text, img))


def surrogate(string):
    return ''.join(c if c <= '\uffff' else ''.join(
                   chr(x) for x in struct.unpack('>2H', c.encode('utf-16be'))) for c in string)


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
            canvas.add_comment(surrogate(comment))

    server_sock.close()


def task(root, canvas):
    canvas.draw()
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
