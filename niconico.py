import math
import random
import select
import struct
import socket
import tkinter as tk
import threading

TRANSPARENT_COLOR = '#010101'
TEXT_COLOR = '#f0f0f0'
FONT_SIZE = 40

labels = []
root = tk.Tk()
running = True


class AnimatingLabel(tk.Label):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.relx = 1.0
        self.rely = random.random() * 0.95
        length = len(kwargs['text'])
        self.stepx = -0.0125 * min(2, max(1, math.log(max(1, length) / 7)))

    def draw(self):
        self.relx += self.stepx
        self.place(relx=self.relx, rely=self.rely)


def task():
    global labels
    for label in labels:
        if label in root.children.values():
            label.draw()
            right = label.winfo_x() + label.winfo_width()
            if right < 0:
                label.destroy()
                labels.remove(label)

    root.after(30, task)


def recieve_comments():
    global labels, root, running
    s = socket.socket()
    s.bind(('', 2525))
    s.listen(5)

    while running:
        ready, _, _ = select.select([s], [], [], 1)
        if ready:
            ss, addr = s.accept()
            comment = ss.recv(1024 * 10).decode().strip()
            ss.close()
            print(comment)
            surrogated = ''.join(c if c <= '\uffff' else ''.join(
                chr(x) for x in struct.unpack('>2H', c.encode('utf-16be'))) for c in comment)
            label = AnimatingLabel(
                root, text=surrogated, bg=TRANSPARENT_COLOR, fg=TEXT_COLOR, font=('', FONT_SIZE, 'bold'))
            labels.append(label)

    s.close()


def main():
    global labels, root, running
    root.title('comment')
    root.wm_attributes('-transparentcolor', TRANSPARENT_COLOR)
    root.config(bg=TRANSPARENT_COLOR)
    root.wm_attributes('-fullscreen', True)
    root.wm_attributes('-topmost', True)

    label = AnimatingLabel(
        root, text='はろーわーるど', bg=TRANSPARENT_COLOR, fg=TEXT_COLOR, font=('', FONT_SIZE, 'bold'))
    labels.append(label)

    recieve_thread = threading.Thread(target=recieve_comments)
    recieve_thread.start()

    root.after(30, task)
    root.mainloop()

    running = False


if __name__ == '__main__':
    main()
