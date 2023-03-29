import base64
import datetime
import io
import os
import numpy as np
import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
import cv2
import csv
import tkinter as tk
from ttkwidgets.autocomplete import AutocompleteEntry
from PIL import Image, ImageTk
from io import BytesIO
# import pandas as pd

# When new icons get added to the database, update the text document and JSON.
print("Today is " + datetime.datetime.now().strftime("%B %d, %Y %H:%M:%S"))


class JSONViewer:
    def __init__(self, parent, filename):
        main_frame = tk.Frame(parent, bg="gray30")
        main_frame.pack(fill='both', expand=1)

        self.container = tk.Canvas(main_frame, bg="gray30", bd=0, highlightthickness=0, relief='ridge')
        self.container.pack(side='left', fill='both', expand=1)

        # Add a Scrollbar(horizontal)
        self.v = tk.Scrollbar(main_frame, orient='vertical', command=self.container.yview)
        self.v.pack(side='right', fill='y')

        self.container.configure(yscrollcommand=self.v.set)
        self.container.bind('<Configure>', lambda e: self.container.configure(scrollregion=self.container.bbox('all')))

        self.f = open(filename)
        self.data = json.load(self.f)
        self.f.close()
        self.items = self.data['items']

        # There are 1589 items.
        # I cropped it down to 1112 items.

        # print(items)
        # Breaks at index 265
        for i in range(len(self.items)):
            self.frame = tk.Frame(self.container, bg="gray30")
            self.container.create_window((2, i * 70), window=self.frame, anchor="nw")

            self.canvas2 = tk.Canvas(self.frame, bg="gray30", bd=0, highlightthickness=0, relief='ridge')
            self.b64img = self.items[i]['base64'].split(",")
            self.im_file = io.BytesIO(base64.decodebytes(bytes(self.b64img[1], 'utf-8')))
            self.img = Image.open(self.im_file).resize((70, 70))
            self.img_check = Image.open(self.im_file)
            self.tkimage = ImageTk.PhotoImage(self.img_check)

            self.img_tk = ImageTk.PhotoImage(self.img)
            self.img_label = tk.Label(self.canvas2, bg='gray30', font=('Times', 21), image=self.img_tk)
            self.img_label.image = self.img_tk
            self.label = tk.Label(self.canvas2, bg='gray30', font=('Times', 18), text=self.items[i]['name'] + " " + str(i) + "  Image size: x: " + str(self.tkimage.width()) + " y: " + str(self.tkimage.height()))
            self.img_label.grid(row=1, column=1)
            self.label.grid(row=1, column=2)
            self.canvas2.pack()

        self.v.config(command=self.container.yview)

        # https://stackoverflow.com/a/37858368

        main_frame.bind('<Enter>', self._bound_to_mousewheel)
        main_frame.bind('<Leave>', self._unbound_to_mousewheel)

    def _bound_to_mousewheel(self, event):
        self.container.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbound_to_mousewheel(self, event):
        self.container.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        self.container.yview_scroll(int(-1 * (event.delta / 120)), "units")


class ImageCropper:
    def __init__(self, parent, image, item_txt, row, col, xincrease, yincrease, save_file):
        main_frame = tk.Frame(parent, background="gray20")
        main_frame.pack()

        self.images_and_items = self.crop_reward(image, item_txt, row, col, xincrease, yincrease)

        print(len(self.images_and_items[0]))

        self.counter = 0
        self.bootup = False
        self.name = []
        self.base64 = []

        self.color = "gray20"

        self.c_top = tk.Canvas(main_frame, background=self.color, highlightbackground=self.color, bd=0, highlightthickness=0, relief='ridge')
        blue, green, red = cv2.split(self.images_and_items[0][0])
        im = Image.fromarray(cv2.merge((red, green, blue)))
        self.imgtk = ImageTk.PhotoImage(image=im.resize((100, 100)))
        self.img_label = tk.Label(self.c_top, bg=self.color, font=('Times', 21), image=self.imgtk)
        self.label = tk.Label(self.c_top, bg=self.color, font=('Times', 21), text='Item names')
        self.entry = AutocompleteEntry(main_frame, width=30, background="gray50", font=('Times', 18), completevalues=self.images_and_items[1])


        self.c_buttons = tk.Canvas(main_frame, background=self.color, highlightbackground=self.color, bd=0, highlightthickness=0, relief='ridge')
        self.btn_submit = tk.Button(self.c_buttons, text="Submit", command=lambda: self.change_image(" "), activebackground="#1c8170", font=15, bg="#30d7bb")
        self.btn_skip = tk.Button(self.c_buttons, text="Skip", command=lambda: self.change_image("skip"), activebackground="#1c8170", font=15, bg="#30d7bb")
        self.btn_rollback = tk.Button(self.c_buttons, text="Rollback", command=lambda: self.rollback(), activebackground="#1c8170", font=15, bg="#30d7bb")
        self.btn_generate = tk.Button(self.c_buttons, text="Generate\nJSON", command=lambda: self.generate(save_file), activebackground="#1c8170", font=15, bg="#30d7bb")
        self.label_blank1 = tk.Label(self.c_buttons, bg=self.color, font=('Times', 21), text='    ')
        self.label_blank2 = tk.Label(self.c_buttons, bg=self.color, font=('Times', 21), text='    ')
        self.label_blank3 = tk.Label(self.c_buttons, bg=self.color, font=('Times', 10), text='    ')

        self.entry.bind('<Return>', self.change_image)

        self.c_top.pack()
        self.img_label.grid(row=1, column=1)
        self.label.grid(row=1, column=2)
        self.entry.pack()
        self.c_buttons.pack()
        self.btn_submit.grid(row=1, column=1)
        self.label_blank1.grid(row=1, column=2)
        self.btn_skip.grid(row=1, column=3)
        self.label_blank3.grid(row=2, column=3)
        self.btn_rollback.grid(row=3, column=1)
        self.label_blank1.grid(row=3, column=2)
        self.btn_generate.grid(row=3, column=3)

        self.bootup = True

    def crop_reward(self, image, item_txt, row, col, xincrease, yincrease):
        item_list = []
        with open(item_txt, "r") as f:
            while f:
                val = f.readline()
                if val == "":
                    break
                item_list.append(val.replace("\n", ""))

        img = cv2.imread(image)

        x = 0
        y = 0
        image_list = []
        try:
            for i in range(row):
                for j in range(col):
                    cropped_image = img[x:x + 32, y:y + 32]
                    image_list.append(cropped_image)
                    y += yincrease
                x += xincrease
                y = 0
        finally:
            return [image_list, item_list]


    def change_image(self, instruction):
        if not self.bootup:
            return

        if instruction == "skip":
            self.name.append("skip")
            self.base64.append("skip")
            self.counter += 1
            print(self.counter)
            blue, green, red = cv2.split(self.images_and_items[0][self.counter])
            new_img = ImageTk.PhotoImage(image=Image.fromarray(cv2.merge((red, green, blue))).resize((100, 100)))
            self.img_label.configure(image=new_img)
            self.img_label.image = new_img
            self.entry.delete(0, 'end')
            return

        retval, buffer_img = cv2.imencode(".png", self.images_and_items[0][self.counter])
        newb64img = base64.b64encode(buffer_img).decode()
        self.base64.append("data:image/png;base64," + newb64img)

        #cv2.imshow("cropped image", self.images_and_items[0][self.counter])
        #cv2.waitKey()
        self.name.append(self.entry.get())
        print("data:image/png;base64," + newb64img)

        self.counter += 1
        print(self.counter)
        blue, green, red = cv2.split(self.images_and_items[0][self.counter])
        new_img = ImageTk.PhotoImage(image=Image.fromarray(cv2.merge((red, green, blue))).resize((100, 100)))
        self.img_label.configure(image=new_img)
        self.img_label.image = new_img
        self.entry.delete(0, 'end')

    def rollback(self):
        try:
            self.name.pop()
            self.base64.pop()
            self.counter -= 1
        except Exception as e:
            pass

        print(self.counter)
        blue, green, red = cv2.split(self.images_and_items[0][self.counter])
        new_img = ImageTk.PhotoImage(image=Image.fromarray(cv2.merge((red, green, blue))).resize((100, 100)))
        self.img_label.configure(image=new_img)
        self.img_label.image = new_img
        self.entry.delete(0, 'end')

    def generate(self, save_file):
        if not self.bootup:
            return
        items = []
        for i in range(len(self.name)):
            if(self.name[i] != "skip" and self.base64[i] != "skip"):
                items.append({"name": self.name[i], "base64": self.base64[i]})

        data = {"items": items}
        with open(save_file, "w") as f:
            json.dump(data, f, indent=4)


def pull_from_server():
    print("Running...")

    try:
        # Sorry, can't give this link.
        with open("Results/dalabase_link.txt", 'r') as file:
            site = file.readline().strip('\n')
        response = requests.get(site)
    except Exception:
        raise "Server is not active. Ending script."


    print("Site check done.")
    print("Processing data...")

    Path("Results").mkdir(parents=True, exist_ok=True)

    soup = BeautifulSoup(response.text, 'html.parser')
    img_tags = soup.find_all('img')
    imgs = [img['src'] for img in img_tags]

    p_tags = soup.find_all('p')
    ps = [str(p.text.encode('utf-8')) for p in p_tags]

    base_list = []
    for img in imgs:
        # filename = re.search(r'^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$', url)
        base_list.append("{}".format(img))

    image_count = 0
    image_list = []
    with open("Base64Vals.txt", "w") as f:
        for i in range(len(base_list)):
            image_list.append(str(base_list[i]))
            f.write(str(base_list[i]))
            if i != (len(base_list)-1):
                f.write('\n')
            image_count += 1
        f.close()

    name_list = []
    tier_list = []
    with open("ItemNameVals.txt", "w") as f:
        for i in range(len(ps)):
            temp = ps[i].split(':')
            temp[1] = temp[1].replace(' tier', "")
            temp[1] = temp[1][1:]
            temp[2] = temp[2][1:]
            temp[2] = temp[2].replace('\'', "")
            name_list.append(temp[1])
            tier_list.append(temp[2])
            # print(temp[2])
            f.write(temp[1])
            if i != (len(ps)-1):
                f.write('\n')

    any_tier = []
    easy = []
    medium = []
    hard = []
    elite = []
    master = []
    for i in range(len(image_list)):
        if tier_list[i] == "any":
            temp = {"name": name_list[i], "base64": base_list[i]}
            any_tier.append(temp)

        elif tier_list[i] == "easy":
            temp = {"name": name_list[i], "base64": base_list[i]}
            easy.append(temp)

        elif tier_list[i] == "medium":
            temp = {"name": name_list[i], "base64": base_list[i]}
            medium.append(temp)

        elif tier_list[i] == "hard":
            temp = {"name": name_list[i], "base64": base_list[i]}
            hard.append(temp)

        elif tier_list[i] == "elite":
            temp = {"name": name_list[i], "base64": base_list[i]}
            elite.append(temp)

        elif tier_list[i] == "master":
            temp = {"name": name_list[i], "base64": base_list[i]}
            master.append(temp)

    data = {
        "any": any_tier,
        "easy": easy,
        "medium": medium,
        "hard": hard,
        "elite": elite,
        "master": master
    }

    filename = "ItemsAndImages ("+datetime.datetime.now().strftime("%Y-%m-%d--%H-%M-%S")+").json"
    with open("Results/"+filename, "w") as f:
        json.dump(data, f, indent=4)

    print("Done!")
    print("There are "+str(image_count)+" images in the Dalabase")


def values():
    new_list = []
    item_list = []
    with open("newlist.txt", "r") as f:
        while f:
            val = f.readline()
            if val == "":
                break
            item_list.append(val)


    seen = set()
    for i in range(len(item_list)):
        if item_list[i] not in seen:
            seen.add(item_list[i])
            new_list.append(item_list[i].replace("\n", ""))

    tab_list = []
    with open("tab.txt", "r") as f:
        while f:
            val = str(f.readline())
            if val == "":
                break
            else:
                val = int(val)
                if val == 1:
                    tab_list.append("general")
                elif val == 2:
                    tab_list.append("common")
                elif val == 3:
                    tab_list.append("rare")
                elif val == 4:
                    tab_list.append("broadcasts")

    tier_list = []
    quantity_list = []
    with open("tier.txt", "r") as f:
        while f:
            quantity = {}
            val = str(f.readline())
            if val == "":
                break
            vals = val.split(',')
            tier_list.append(vals)

            for i in range(len(vals)):
                quantity[vals[i].replace("\n", "")] = 0
            quantity_list.append(quantity)


    for i in range(len(tier_list)):
        tier_list[i][len(tier_list[i])-1] = tier_list[i][len(tier_list[i])-1].replace("\n", "")

    # with open("newlist.txt", "w") as f:
    #     for i in range(len(new_list)):
    #         f.write(new_list[i]+'\n')
    # print(tab_list)
    # print(new_list)
    # print(tier_list)
    # print(len(new_list))
    # print(len(tab_list))
    # print(len(tier_list))

    data = {}
    for i in range(len(new_list)):
        order = i + 1
        data[new_list[i]] = {"tab": tab_list[i], "tier": tier_list[i], "quantity": quantity_list[i], "order": order}

    #data["EValue"] = 0
    #data["ECount"] = 0
    #data["MValue"] = 0
    #data["MCount"] = 0
    #data["HValue"] = 0
    #data["HCount"] = 0
    #data["ElValue"] = 0
    #data["ElCount"] = 0
    #data["MaValue"] = 0
    #data["MaCount"] = 0

    #TODO: Filename has changed. Add a personal addition
    with open("LocalStorageInit.json", "w") as f:
        json.dump(data, f, indent=4)


def remove_underscores(filepath):
    # https://stackoverflow.com/questions/44072332/
    paths = (os.path.join(root, filename)
             for root, _, filenames in os.walk(filepath)
             for filename in filenames)

    # The keys of the dictionary are the values to replace, each corresponding
    # item is the string to replace it with
    replacements = {'.File': ' ',
                    'Generic': ' '}

    for path in paths:
        # Copy the path name to apply changes (if any) to
        newname = path
        # Loop over the dictionary elements, applying the replacements
        for i in replacements.items():
            newname = newname.replace("_", " ")
        if newname != path:
            os.rename(path, newname)
        print(newname)


def blue_to_tan():
    f = open("JSON images/ItemsAndImagesReorganized.json")
    filename = "ItemsAndImagesLegacyReorganized.json"
    data = json.load(f)
    anyvals = data["any"]
    easy = data["easy"]
    medium = data["medium"]
    hard = data["hard"]
    elite = data["elite"]
    master = data["master"]

    # print(anyvals)
    # print(easy)
    # print(medium)
    # print(hard)
    # print(elite)
    # print(master)

    leg_anyvals = []
    leg_easy = []
    leg_medium = []
    leg_hard = []
    leg_elite = []
    leg_master = []
    tan = (62, 53, 40)
    blue = (10, 31, 41)

    # print(anyvals[0])
    for i in range(len(anyvals)):
        b64img = anyvals[i]['base64'].split(",")
        if len(b64img[1]) % 4 == 0:
            b64img[1] += '='*(4 - (len(b64img[1]) % 4))
        im_bytes = base64.b64decode(b64img[1])
        im_arr = np.frombuffer(im_bytes, dtype=np.uint8)
        img = cv2.imdecode(im_arr, flags=cv2.IMREAD_COLOR)
        height, width, _ = img.shape
        for j in range(height):
            # print("in height")
            for k in range(width):
                # print("in width"+str(k))
                # img[i,j] is the RGB pixel at position (i, j)
                # check if it's [0, 0, 0] and replace with [255, 255, 255] if so
                if img[j, k].sum() == 82:
                    img[j, k] = [40, 53, 62]
        cv2.imwrite("check.png", img)
        retval, buffer_img = cv2.imencode(".png", img)
        newb64img = base64.b64encode(buffer_img).decode()
        newdata = {"name": anyvals[i]['name'], "base64": "data:image/png;base64,"+newb64img}
        leg_anyvals.append(newdata)

    #print(leg_anyvals)

    for i in range(len(easy)):
        b64img = easy[i]['base64'].split(",")
        if len(b64img[1]) % 4 == 0:
            b64img[1] += '='*(4 - (len(b64img[1]) % 4))
        im_bytes = base64.b64decode(b64img[1])
        im_arr = np.frombuffer(im_bytes, dtype=np.uint8)
        img = cv2.imdecode(im_arr, flags=cv2.IMREAD_COLOR)
        height, width, _ = img.shape
        for j in range(height):
            # print("in height")
            for k in range(width):
                # print("in width"+str(k))
                # img[i,j] is the RGB pixel at position (i, j)
                # check if it's [0, 0, 0] and replace with [255, 255, 255] if so
                if img[j, k].sum() == 82:
                    img[j, k] = [40, 53, 62]
        cv2.imwrite("check.png", img)
        retval, buffer_img = cv2.imencode(".png", img)
        newb64img = base64.b64encode(buffer_img).decode()
        newdata = {"name": easy[i]['name'], "base64": "data:image/png;base64,"+newb64img}
        leg_easy.append(newdata)
    #print(leg_easy)

    for i in range(len(medium)):
        b64img = medium[i]['base64'].split(",")
        if len(b64img[1]) % 4 == 0:
            b64img[1] += '='*(4 - (len(b64img[1]) % 4))
        im_bytes = base64.b64decode(b64img[1])
        im_arr = np.frombuffer(im_bytes, dtype=np.uint8)
        img = cv2.imdecode(im_arr, flags=cv2.IMREAD_COLOR)
        height, width, _ = img.shape
        for j in range(height):
            # print("in height")
            for k in range(width):
                # print("in width"+str(k))
                # img[i,j] is the RGB pixel at position (i, j)
                # check if it's [0, 0, 0] and replace with [255, 255, 255] if so
                if img[j, k].sum() == 82:
                    img[j, k] = [40, 53, 62]
        cv2.imwrite("check.png", img)
        retval, buffer_img = cv2.imencode(".png", img)
        newb64img = base64.b64encode(buffer_img).decode()
        newdata = {"name": medium[i]['name'], "base64": "data:image/png;base64,"+newb64img}
        leg_medium.append(newdata)
    #print(leg_medium)

    for i in range(len(hard)):
        b64img = hard[i]['base64'].split(",")
        if len(b64img[1]) % 4 == 0:
            b64img[1] += '='*(4 - (len(b64img[1]) % 4))
        im_bytes = base64.b64decode(b64img[1])
        im_arr = np.frombuffer(im_bytes, dtype=np.uint8)
        img = cv2.imdecode(im_arr, flags=cv2.IMREAD_COLOR)
        height, width, _ = img.shape
        for j in range(height):
            # print("in height")
            for k in range(width):
                # print("in width"+str(k))
                # img[i,j] is the RGB pixel at position (i, j)
                # check if it's [0, 0, 0] and replace with [255, 255, 255] if so
                if img[j, k].sum() == 82:
                    img[j, k] = [40, 53, 62]
        cv2.imwrite("check.png", img)
        retval, buffer_img = cv2.imencode(".png", img)
        newb64img = base64.b64encode(buffer_img).decode()
        newdata = {"name": hard[i]['name'], "base64": "data:image/png;base64,"+newb64img}
        leg_hard.append(newdata)
    #print(leg_hard)

    for i in range(len(elite)):
        b64img = elite[i]['base64'].split(",")
        if len(b64img[1]) % 4 == 0:
            b64img[1] += '='*(4 - (len(b64img[1]) % 4))
        im_bytes = base64.b64decode(b64img[1])
        im_arr = np.frombuffer(im_bytes, dtype=np.uint8)
        img = cv2.imdecode(im_arr, flags=cv2.IMREAD_COLOR)
        height, width, _ = img.shape
        for j in range(height):
            # print("in height")
            for k in range(width):
                # print("in width"+str(k))
                # img[i,j] is the RGB pixel at position (i, j)
                # check if it's [0, 0, 0] and replace with [255, 255, 255] if so
                if img[j, k].sum() == 82:
                    img[j, k] = [40, 53, 62]
        cv2.imwrite("check.png", img)
        retval, buffer_img = cv2.imencode(".png", img)
        newb64img = base64.b64encode(buffer_img).decode()
        newdata = {"name": elite[i]['name'], "base64": "data:image/png;base64,"+newb64img}
        leg_elite.append(newdata)
    #print(leg_elite)

    for i in range(len(master)):
        b64img = master[i]['base64'].split(",")
        if len(b64img[1]) % 4 == 0:
            b64img[1] += '='*(4 - (len(b64img[1]) % 4))
        im_bytes = base64.b64decode(b64img[1])
        im_arr = np.frombuffer(im_bytes, dtype=np.uint8)
        img = cv2.imdecode(im_arr, flags=cv2.IMREAD_COLOR)
        height, width, _ = img.shape
        for j in range(height):
            # print("in height")
            for k in range(width):
                # print("in width"+str(k))
                # img[i,j] is the RGB pixel at position (i, j)
                # check if it's [0, 0, 0] and replace with [255, 255, 255] if so
                if img[j, k].sum() == 82:
                    img[j, k] = [40, 53, 62]
        cv2.imwrite("check.png", img)
        retval, buffer_img = cv2.imencode(".png", img)
        newb64img = base64.b64encode(buffer_img).decode()
        newdata = {"name": master[i]['name'], "base64": "data:image/png;base64,"+newb64img}
        leg_master.append(newdata)

    #print(leg_master)
    data = {
        "any": leg_anyvals,
        "easy": leg_easy,
        "medium": leg_medium,
        "hard": leg_hard,
        "elite": leg_elite,
        "master": leg_master
    }

    with open("JSON images/" + filename, "w") as f:
        json.dump(data, f, indent=4)


def base64_to_png():
    f = open("JSON images/ItemsAndImagesReorganized.json")
    data = json.load(f)
    anyvals = data["any"]
    easy = data["easy"]
    medium = data["medium"]
    hard = data["hard"]
    elite = data["elite"]
    master = data["master"]

    # print(anyvals)
    # print(easy)
    # print(medium)
    # print(hard)
    # print(elite)
    # print(master)

    leg_anyvals = []
    leg_easy = []
    leg_medium = []
    leg_hard = []
    leg_elite = []
    leg_master = []
    tan = (62, 53, 40)
    blue = (10, 31, 41)

    # print(anyvals[0])
    numbers = 4
    for i in range(len(anyvals)):
        b64img = anyvals[i]['base64'].split(",")
        if len(b64img[1]) % 4 == 0:
            b64img[1] += '=' * (4 - (len(b64img[1]) % 4))
        im_bytes = base64.b64decode(b64img[1])
        im_arr = np.frombuffer(im_bytes, dtype=np.uint8)
        img = cv2.imdecode(im_arr, flags=cv2.IMREAD_COLOR)
        cv2.imwrite("JSON images/("+str(numbers)+")"+anyvals[i]['name']+".png", img)
        numbers += 4

    numbers += 2
    for i in range(len(easy)):
        b64img = easy[i]['base64'].split(",")
        if len(b64img[1]) % 4 == 0:
            b64img[1] += '=' * (4 - (len(b64img[1]) % 4))
        im_bytes = base64.b64decode(b64img[1])
        im_arr = np.frombuffer(im_bytes, dtype=np.uint8)
        img = cv2.imdecode(im_arr, flags=cv2.IMREAD_COLOR)
        cv2.imwrite("JSON images/("+str(numbers)+")"+easy[i]['name']+".png", img)
        numbers += 4

    numbers += 2
    for i in range(len(medium)):
        b64img = medium[i]['base64'].split(",")
        if len(b64img[1]) % 4 == 0:
            b64img[1] += '=' * (4 - (len(b64img[1]) % 4))
        im_bytes = base64.b64decode(b64img[1])
        im_arr = np.frombuffer(im_bytes, dtype=np.uint8)
        img = cv2.imdecode(im_arr, flags=cv2.IMREAD_COLOR)
        cv2.imwrite("JSON images/("+str(numbers)+")"+medium[i]['name']+".png", img)
        numbers += 4

    for i in range(len(hard)):
        b64img = hard[i]['base64'].split(",")
        if len(b64img[1]) % 4 == 0:
            b64img[1] += '=' * (4 - (len(b64img[1]) % 4))
        im_bytes = base64.b64decode(b64img[1])
        im_arr = np.frombuffer(im_bytes, dtype=np.uint8)
        img = cv2.imdecode(im_arr, flags=cv2.IMREAD_COLOR)
        cv2.imwrite("JSON images/("+str(numbers)+")"+hard[i]['name']+".png", img)
        numbers += 4

    numbers += 2

    for i in range(len(elite)):
        b64img = elite[i]['base64'].split(",")
        if len(b64img[1]) % 4 == 0:
            b64img[1] += '=' * (4 - (len(b64img[1]) % 4))
        im_bytes = base64.b64decode(b64img[1])
        im_arr = np.frombuffer(im_bytes, dtype=np.uint8)
        img = cv2.imdecode(im_arr, flags=cv2.IMREAD_COLOR)
        cv2.imwrite("JSON images/("+str(numbers)+")"+elite[i]['name']+".png", img)
        numbers += 4

    numbers += 2

    for i in range(len(master)):
        b64img = master[i]['base64'].split(",")
        if len(b64img[1]) % 4 == 0:
            b64img[1] += '=' * (4 - (len(b64img[1]) % 4))
        im_bytes = base64.b64decode(b64img[1])
        im_arr = np.frombuffer(im_bytes, dtype=np.uint8)
        img = cv2.imdecode(im_arr, flags=cv2.IMREAD_COLOR)
        cv2.imwrite("JSON images/(" + str(numbers) + ")" + master[i]['name'] + ".png", img)
        numbers += 4

    numbers += 2

    # print(leg_anyvals)


def csv_to_json():
    any_arr = []
    easy_arr = []
    medium_arr = []
    hard_arr = []
    elite_arr = []
    master_arr = []

    with open("direct db csvs/any.csv") as csvfile:
        temp = csv.reader(csvfile)
        next(temp, None)
        for row in temp:
            any_arr.append({"name": row[1], "base64": row[4]})

    with open("direct db csvs/easy.csv") as csvfile:
        temp = csv.reader(csvfile)
        next(temp, None)
        for row in temp:
            easy_arr.append({"name": row[1], "base64": row[4]})

    with open("direct db csvs/medium.csv") as csvfile:
        temp = csv.reader(csvfile)
        next(temp, None)
        for row in temp:
            medium_arr.append({"name": row[1], "base64": row[4]})

    with open("direct db csvs/hard.csv") as csvfile:
        temp = csv.reader(csvfile)
        next(temp, None)
        for row in temp:
            hard_arr.append({"name": row[1], "base64": row[4]})

    with open("direct db csvs/elite.csv") as csvfile:
        temp = csv.reader(csvfile)
        next(temp, None)
        for row in temp:
            elite_arr.append({"name": row[1], "base64": row[4]})

    with open("direct db csvs/master.csv") as csvfile:
        temp = csv.reader(csvfile)
        next(temp, None)
        for row in temp:
            master_arr.append({"name": row[1], "base64": row[4]})

    data = {
        "any": any_arr,
        "easy": easy_arr,
        "medium": medium_arr,
        "hard": hard_arr,
        "elite": elite_arr,
        "master": master_arr
    }

    filename = "ItemsAndImagesAlt64.json"
    with open("Results/" + filename, "w") as f:
        json.dump(data, f, indent=4)

    pass


def values_barrows():
    new_list = []
    item_list = []
    with open("barrows names/barrowsitems.txt", "r") as f:
        while f:
            val = f.readline()
            if val == "":
                break
            item_list.append(val)


    seen = set()
    for i in range(len(item_list)):
        if item_list[i] not in seen:
            seen.add(item_list[i])
            new_list.append(item_list[i].replace("\n", ""))

    tab_list = []
    with open("barrows names/barrowstab.txt", "r") as f:
        while f:
            val = str(f.readline())
            if val == "":
                break
            else:
                val = int(val)
                if val == 1:
                    tab_list.append("equipment")
                elif val == 2:
                    tab_list.append("general")

    data = {}
    for i in range(len(new_list)):
        data[new_list[i]] = {"tab": tab_list[i], "quantity": 0, "order": i + 1}

    #TODO: Filename has changed. Add a personal addition
    with open("barrows names/LocalStorageBarrowsInit.json", "w") as f:
        json.dump(data, f, indent=4)


def blue_to_tan_barrows():
    f = open("Results/ItemsAndImagesBarrows.json")
    filename = "ItemsAndImagesBarrowsLegacy.json"
    data = json.load(f)
    itemsvals = data["items"]

    leg_itemsvals = []
    tan = (62, 53, 40)
    blue = (10, 31, 41)

    for i in range(len(itemsvals)):
        b64img = itemsvals[i]['base64'].split(",")
        if len(b64img[1]) % 4 == 0:
            b64img[1] += '='*(4 - (len(b64img[1]) % 4))
        im_bytes = base64.b64decode(b64img[1])
        im_arr = np.frombuffer(im_bytes, dtype=np.uint8)
        img = cv2.imdecode(im_arr, flags=cv2.IMREAD_COLOR)
        height, width, _ = img.shape
        for j in range(height):
            # print("in height")
            for k in range(width):
                # print("in width"+str(k))
                # img[i,j] is the RGB pixel at position (i, j)
                # check if it's [0, 0, 0] and replace with [255, 255, 255] if so
                if img[j, k].sum() == 82:
                    img[j, k] = [40, 53, 62]
        cv2.imwrite("check.png", img)
        retval, buffer_img = cv2.imencode(".png", img)
        newb64img = base64.b64encode(buffer_img).decode()
        newdata = {"name": itemsvals[i]['name'], "base64": "data:image/png;base64,"+newb64img}
        leg_itemsvals.append(newdata)

        data = {
            "items": leg_itemsvals
        }

        with open("Results/" + filename, "w") as f:
            json.dump(data, f, indent=4)


def sort_rewards_and_bank():
    f1 = open("tetra crops/ItemsAndImagesTetraRewards.json")
    f2 = open("tetra crops/ItemsAndImagesTetraBank.json")
    f3 = open("tetra crops/ItemsAndImagesTetraFive.json")
    filename = "ItemsAndImagesTetra.json"
    data1 = json.load(f1)
    data2 = json.load(f2)
    data3 = json.load(f3)
    rewards_vals = data1["items"]
    bank_vals = data2["items"]
    five_vals = data3["items"]


    item_list = []
    with open("tetra crops/tetra item names.txt", "r") as f:
        while f:
            val = f.readline()
            if val == "":
                break
            item_list.append(val.replace("\n", ""))

    item_vals = []
    for i in range(len(item_list)):
        for j in range(len(rewards_vals), 0, -1):
            temp = rewards_vals[j - 1]["name"]
            if temp == item_list[i]:
                temp = rewards_vals.pop(j - 1)
                item_vals.append(temp)
        for j in range(len(bank_vals), 0, -1):
            temp = bank_vals[j - 1]["name"]
            if temp == item_list[i]:
                temp = bank_vals.pop(j - 1)
                item_vals.append(temp)

        for j in range(len(five_vals), 0, -1):
            temp = five_vals[j - 1]["name"]
            if temp == item_list[i]:
                temp = five_vals.pop(j - 1)
                item_vals.append(temp)

    data = {"items": item_vals}
    with open("JSON images/" + filename, "w") as f:
        json.dump(data, f, indent=4)


def blue_to_tan_tetras():
    f = open("JSON images/ItemsAndImagesTetra.json")
    filename = "ItemsAndImagesTetraLegacy.json"
    data = json.load(f)
    itemsvals = data["items"]

    leg_itemsvals = []
    tan = (62, 53, 40)
    blue = (10, 31, 41)

    for i in range(len(itemsvals)):
        b64img = itemsvals[i]['base64'].split(",")
        if len(b64img[1]) % 4 == 0:
            b64img[1] += '='*(4 - (len(b64img[1]) % 4))
        im_bytes = base64.b64decode(b64img[1])
        im_arr = np.frombuffer(im_bytes, dtype=np.uint8)
        img = cv2.imdecode(im_arr, flags=cv2.IMREAD_COLOR)
        height, width, _ = img.shape
        for j in range(height):
            # print("in height")
            for k in range(width):
                # print("in width"+str(k))
                # img[i,j] is the RGB pixel at position (i, j)
                # check if it's [0, 0, 0] and replace with [255, 255, 255] if so
                if img[j, k].sum() == 82:
                    img[j, k] = [40, 53, 62]
        cv2.imwrite("check.png", img)
        retval, buffer_img = cv2.imencode(".png", img)
        newb64img = base64.b64encode(buffer_img).decode()
        newdata = {"name": itemsvals[i]['name'], "base64": "data:image/png;base64,"+newb64img}
        leg_itemsvals.append(newdata)

        data = {
            "items": leg_itemsvals
        }

        with open("JSON images/" + filename, "w") as f:
            json.dump(data, f, indent=4)


def values_tetra():
    new_list = []
    item_list = []
    with open("tetra names/tetraitems.txt", "r") as f:
        while f:
            val = f.readline()
            if val == "":
                break
            item_list.append(val)


    seen = set()
    for i in range(len(item_list)):
        if item_list[i] not in seen:
            seen.add(item_list[i])
            new_list.append(item_list[i].replace("\n", ""))

    tab_list = []
    with open("tetra names/tetratab.txt", "r") as f:
        while f:
            val = str(f.readline())
            if val == "":
                break
            else:
                val = int(val)
                if val == 1:
                    tab_list.append("artifacts")
                elif val == 2:
                    tab_list.append("materials")
                elif val == 3:
                    tab_list.append("miscellaneous")

    data = {}
    for i in range(len(new_list)):
        data[new_list[i]] = {"tab": tab_list[i], "quantity": 0, "order": i + 1}

    #TODO: Filename has changed. Add a personal addition
    with open("tetra names/LocalStorageTetraInit.json", "w") as f:
        json.dump(data, f, indent=4)


def duplicate_remover():
    f = open("JSON images/ItemsAndImagesTetra.json")
    filename = "ItemsAndImagesTetraClean.json"
    data1 = json.load(f)
    rewards_vals = data1["items"]
    f.close()

    temp = []
    for i in range(len(rewards_vals)):
        if rewards_vals[i] not in rewards_vals[i + 1:]:
            temp.append(rewards_vals[i])

    print(len(temp))
    data = {"items": temp}

    with open("tetra names/" + filename, "w") as f:
        json.dump(data, f, indent=4)


def values_crystal():
    new_list = []
    item_list = []
    with open("crystal crops/crystalitems.txt", "r") as f:
        while f:
            val = f.readline()
            if val == "":
                break
            item_list.append(val)

    seen = set()
    for i in range(len(item_list)):
        if item_list[i] not in seen:
            seen.add(item_list[i])
            new_list.append(item_list[i].replace("\n", ""))

    tab_list = []
    with open("crystal crops/crystaltab.txt", "r") as f:
        while f:
            val = str(f.readline())
            if val == "":
                break
            else:
                val = int(val)
                if val == 1:
                    tab_list.append("first")
                elif val == 2:
                    tab_list.append("second")
                elif val == 3:
                    tab_list.append("third")
                elif val == 4:
                    tab_list.append("fourth")

    tier_list = []
    quantity_list = []
    with open("crystal crops/crystaltiers.txt", "r") as f:
        while f:
            quantity = {}
            val = str(f.readline())
            if val == "":
                break
            vals = val.split(',')
            tier_list.append(vals)

            for i in range(len(vals)):
                vals[i] = vals[i].replace("T", "taverley")
                vals[i] = vals[i].replace("P", "prifddinas")
                vals[i] = vals[i].replace("K", "triskelion")
                vals[i] = vals[i].replace("A", "alchemist")
                quantity[vals[i].replace("\n", "")] = 0
            quantity_list.append(quantity)


    for i in range(len(tier_list)):
        tier_list[i][len(tier_list[i])-1] = tier_list[i][len(tier_list[i])-1].replace("\n", "")

    data = {}
    for i in range(len(new_list)):
        order = i + 1
        data[new_list[i]] = {"tab": tab_list[i], "tier": tier_list[i], "quantity": quantity_list[i], "order": order}

    with open("crystal crops/LocalStorageCrystalInit.json", "w") as f:
        json.dump(data, f, indent=4)


def sort_rewards_and_trade():
    f1 = open("Results/ItemsAndImagesCrystalRewards.json")
    f2 = open("Results/ItemsAndImagesCrystalTrade.json")
    filename = "crystal crops/ItemsAndImagesCrystal.json"
    data1 = json.load(f1)
    data2 = json.load(f2)
    rewards_vals = data1["items"]
    trade_vals = data2["items"]

    tav_list = []
    priff_list = []
    trisk_list = []
    alch_list = []

    flist = open("crystal crops/LocalStorageCrystalInit.json")
    datalist = json.load(flist)
    print(datalist)
    for key in datalist.keys():
        for i in range(len(datalist[key]["tier"])):
            if(datalist[key]["tier"][i] == "taverley"):
                tav_list.append(key)
            elif(datalist[key]["tier"][i] == "prifddinas"):
                priff_list.append(key)
            elif(datalist[key]["tier"][i] == "triskelion"):
                trisk_list.append(key)
            elif(datalist[key]["tier"][i] == "alchemist"):
                alch_list.append(key)

    print("Taverley", tav_list)
    print("Prifddinas", priff_list)
    print("Triskelion", trisk_list)
    print("Alchemist", alch_list)

    item_list = []
    with open("crystal crops/crystalitems.txt", "r") as f:
        while f:
            val = f.readline()
            if val == "":
                break
            item_list.append(val.replace("\n", ""))

    tav_vals = []
    for i in range(len(tav_list)):
        for j in range(len(rewards_vals), 0, -1):
            temp = rewards_vals[j - 1]
            if temp["name"] == tav_list[i]:
                tav_vals.append(temp)
        for j in range(len(trade_vals), 0, -1):
            temp = trade_vals[j - 1]
            if temp["name"] == tav_list[i]:
                tav_vals.append(temp)

    priff_vals = []
    for i in range(len(priff_list)):
        for j in range(len(rewards_vals), 0, -1):
            temp = rewards_vals[j - 1]
            if temp["name"] == priff_list[i]:
                priff_vals.append(temp)
        for j in range(len(trade_vals), 0, -1):
            temp = trade_vals[j - 1]
            if temp["name"] == priff_list[i]:
                priff_vals.append(temp)

    trisk_vals = []
    for i in range(len(trisk_list)):
        for j in range(len(rewards_vals), 0, -1):
            temp = rewards_vals[j - 1]
            if temp["name"] == trisk_list[i]:
                trisk_vals.append(temp)
        for j in range(len(trade_vals), 0, -1):
            temp = trade_vals[j - 1]
            if temp["name"] == trisk_list[i]:
                trisk_vals.append(temp)

    alch_vals = []
    for i in range(len(alch_list)):
        for j in range(len(rewards_vals), 0, -1):
            temp = rewards_vals[j - 1]
            if temp["name"] == alch_list[i]:
                alch_vals.append(temp)
        for j in range(len(trade_vals), 0, -1):
            temp = trade_vals[j - 1]
            if temp["name"] == alch_list[i]:
                alch_vals.append(temp)

    data = {"taverley": tav_vals,
            "prifddinas": priff_vals,
            "triskelion": trisk_vals,
            "alchemist": alch_vals}

    print(data)

    with open(filename, "w") as f:
        json.dump(data, f, indent=4)


def duplicate_remover_crystal():
    # f = open("crystal crops/ItemsAndImagesCrystalOneList.json")
    # filename = "crystal crops/ItemsAndImagesCrystalOneList.json"
    # data = json.load(f)
    # rewards_vals = data["items"]
    # f.close()
    #
    # temp = []
    # for i in range(len(rewards_vals)):
    #     if rewards_vals[i] not in rewards_vals[i + 1:]:
    #         print("Adding", rewards_vals[i]["name"])
    #         temp.append(rewards_vals[i])
    #
    # data = {
    #     "items": temp
    # }
    #
    # with open(filename, "w") as f:
    #     json.dump(data, f, indent=4)


    f = open("crystal crops/ItemsAndImagesCrystal.json")
    filename = "crystal crops/ItemsAndImagesCrystal.json"
    data = json.load(f)
    tav_vals = data["taverley"]
    priff_vals = data["prifddinas"]
    trisk_vals = data["triskelion"]
    alch_vals = data["alchemist"]
    f.close()

    tav_temp = []
    for i in range(len(tav_vals)):
        if tav_vals[i] not in tav_vals[i + 1:]:
            tav_temp.append(tav_vals[i])

    priff_temp = []
    for i in range(len(priff_vals)):
        if priff_vals[i] not in priff_vals[i + 1:]:
            priff_temp.append(priff_vals[i])

    trisk_temp = []
    for i in range(len(trisk_vals)):
        if trisk_vals[i] not in trisk_vals[i + 1:]:
            trisk_temp.append(trisk_vals[i])

    alch_temp = []
    for i in range(len(alch_vals)):
        if alch_vals[i] not in alch_vals[i + 1:]:
            alch_temp.append(alch_vals[i])

    data = {
        "taverley": tav_temp,
        "prifddinas": priff_temp,
        "triskelion": trisk_temp,
        "alchemist": alch_temp
    }

    with open(filename, "w") as f:
        json.dump(data, f, indent=4)


    item_vals = []
    for i in range(len(tav_temp)):
        item_vals.append(tav_temp[i])
    for i in range(len(priff_temp)):
        item_vals.append(priff_temp[i])
    for i in range(len(trisk_temp)):
        item_vals.append(trisk_temp[i])
    for i in range(len(alch_temp)):
        item_vals.append(alch_temp[i])

    data = {"items": item_vals}
    with open("crystal crops/ItemsAndImagesCrystalOneList.json", "w") as f:
        json.dump(data, f, indent=4)


def blue_to_tan_crystal():
    f = open("crystal crops/ItemsAndImagesCrystal.json")
    filename = "crystal crops/ItemsAndImagesCrystalLegacy.json"
    data = json.load(f)
    tav_vals = data["taverley"]
    priff_vals = data["prifddinas"]
    trisk_vals = data["triskelion"]
    alch_vals = data["alchemist"]
    f.close()

    leg_tav_vals = []
    leg_priff_vals = []
    leg_trisk_vals = []
    leg_alch_vals = []

    tan = (62, 53, 40)
    blue = (10, 31, 41)

    for i in range(len(tav_vals)):
        b64img = tav_vals[i]['base64'].split(",")
        if len(b64img[1]) % 4 == 0:
            b64img[1] += '='*(4 - (len(b64img[1]) % 4))
        im_bytes = base64.b64decode(b64img[1])
        im_arr = np.frombuffer(im_bytes, dtype=np.uint8)
        img = cv2.imdecode(im_arr, flags=cv2.IMREAD_COLOR)
        height, width, _ = img.shape
        for j in range(height):
            for k in range(width):
                if img[j, k].sum() == 82:
                    img[j, k] = [40, 53, 62]
        cv2.imwrite("check.png", img)
        retval, buffer_img = cv2.imencode(".png", img)
        newb64img = base64.b64encode(buffer_img).decode()
        newdata = {"name": tav_vals[i]['name'], "base64": "data:image/png;base64,"+newb64img}
        leg_tav_vals.append(newdata)

    for i in range(len(priff_vals)):
        b64img = priff_vals[i]['base64'].split(",")
        if len(b64img[1]) % 4 == 0:
            b64img[1] += '='*(4 - (len(b64img[1]) % 4))
        im_bytes = base64.b64decode(b64img[1])
        im_arr = np.frombuffer(im_bytes, dtype=np.uint8)
        img = cv2.imdecode(im_arr, flags=cv2.IMREAD_COLOR)
        height, width, _ = img.shape
        for j in range(height):
            for k in range(width):
                if img[j, k].sum() == 82:
                    img[j, k] = [40, 53, 62]
        cv2.imwrite("check.png", img)
        retval, buffer_img = cv2.imencode(".png", img)
        newb64img = base64.b64encode(buffer_img).decode()
        newdata = {"name": priff_vals[i]['name'], "base64": "data:image/png;base64,"+newb64img}
        leg_priff_vals.append(newdata)

    for i in range(len(trisk_vals)):
        b64img = trisk_vals[i]['base64'].split(",")
        if len(b64img[1]) % 4 == 0:
            b64img[1] += '='*(4 - (len(b64img[1]) % 4))
        im_bytes = base64.b64decode(b64img[1])
        im_arr = np.frombuffer(im_bytes, dtype=np.uint8)
        img = cv2.imdecode(im_arr, flags=cv2.IMREAD_COLOR)
        height, width, _ = img.shape
        for j in range(height):
            for k in range(width):
                if img[j, k].sum() == 82:
                    img[j, k] = [40, 53, 62]
        cv2.imwrite("check.png", img)
        retval, buffer_img = cv2.imencode(".png", img)
        newb64img = base64.b64encode(buffer_img).decode()
        newdata = {"name": trisk_vals[i]['name'], "base64": "data:image/png;base64,"+newb64img}
        leg_trisk_vals.append(newdata)

    for i in range(len(alch_vals)):
        b64img = alch_vals[i]['base64'].split(",")
        if len(b64img[1]) % 4 == 0:
            b64img[1] += '='*(4 - (len(b64img[1]) % 4))
        im_bytes = base64.b64decode(b64img[1])
        im_arr = np.frombuffer(im_bytes, dtype=np.uint8)
        img = cv2.imdecode(im_arr, flags=cv2.IMREAD_COLOR)
        height, width, _ = img.shape
        for j in range(height):
            for k in range(width):
                if img[j, k].sum() == 82:
                    img[j, k] = [40, 53, 62]
        cv2.imwrite("check.png", img)
        retval, buffer_img = cv2.imencode(".png", img)
        newb64img = base64.b64encode(buffer_img).decode()
        newdata = {"name": alch_vals[i]['name'], "base64": "data:image/png;base64,"+newb64img}
        leg_alch_vals.append(newdata)

    data = {
        "taverley": leg_tav_vals,
        "prifddinas": leg_priff_vals,
        "triskelion": leg_trisk_vals,
        "alchemist": leg_alch_vals
    }

    with open(filename, "w") as f:
        json.dump(data, f, indent=4)


    leg_vals = []
    for i in range(len(leg_tav_vals)):
        leg_vals.append(leg_tav_vals[i])
    for i in range(len(leg_priff_vals)):
        leg_vals.append(leg_priff_vals[i])
    for i in range(len(leg_trisk_vals)):
        leg_vals.append(leg_trisk_vals[i])
    for i in range(len(leg_alch_vals)):
        leg_vals.append(leg_alch_vals[i])

    data = {
        "items": leg_vals,
    }

    with open("crystal crops/ItemsAndImagesCrystalLegacyOneList.json", "w") as f:
        json.dump(data, f, indent=4)


choice = 0
while choice == 0:  # TODO: Change to != -1 to loop it
    print("What are you doing?\n\n"
          
          "Clue items below here\n"
          "=====================\n"
          "1 for new json\n"
          "2 for names\n"
          "3 for removing underscores from openlogger image names\n"
          "4 to change blue to tan\n"
          "5 to turn base64 to png\n"
          "6 to turn csvs into jsons\n\n"
          
          
          "Barrows items below here\n"
          "========================\n"
          "7 to remove underscores from barrows image names\n"
          "8 for barrows names\n"
          "9 for cropping assorted barrows items png\n"
          "10 to change blue to tan for barrows\n"
          "21 to see barrows items\n\n"
    
          
          "Tetra items below here\n"
          "======================\n"
          "11 to crop tetra reward artifact image\n"
          "12 to crop tetra bank artifact image\n"
          "13 to sort rewards and bank JSONs\n"
          "14 to visually see new Tetra JSON\n"
          "15 to crop five material images\n"
          "16 to change blue to tan for tetras\n"
          "17 for tetra names\n"
          "18 to remove underscores from tetra image names\n"
          "19 to remove duplicates from JSON\n"
          "20 to visually see new legacy Tetra JSON\n\n"
            
            
          "Crystal items below here\n"
          "======================\n"
          "22 for crystal names\n"
          "23 to crop crystal reward image\n"
          "24 to crop crystal trade image\n"
          "25 to merge reward and trade JSONs + sort by chest\n"
          "26 to remove duplicates from JSON\n"
          "27 to display crystal items\n"
          "28 to change blue to tan for crystal items\n"
          "29 to display legacy crystal items\n"
          "30 to remove underscores from crystal names\n\n"
          
          
          
          "-1 to exit\n"

          )

    choice = int(input())

    # OpenLogger:
    try:
        if choice == 1:
            pull_from_server()

        elif choice == 2:
            values()

        elif choice == 3:
            remove_underscores('clue images/')

        elif choice == 4:
            blue_to_tan()

        elif choice == 5:
            base64_to_png()

        elif choice == 6:
            csv_to_json()
    except Exception as e:
        print(e)

    # BarrowsLogger
    try:
        if choice == 7:
            remove_underscores('/barrows images')

        elif choice == 8:
            values_barrows()

        elif choice == 9:
            if __name__ == '__main__':
                root = tk.Tk()
                root.title("Image cropper and assigner")
                a = ImageCropper(root,
                                 'barrows crops/assorted_barrows_items_2.png',
                                 "barrows names/barrowsitems.txt",
                                 13, 4, 32, 47,
                                 'Results/ItemsAndImagesBarrows.json')
                root.configure(bg="gray20")
                root.mainloop()

        elif choice == 10:
            blue_to_tan_barrows()

        elif choice == 21:
            if __name__ == '__main__':
                root = tk.Tk()
                root.title("JSONViewer")
                filename = "Results/ItemsAndImagesBarrows.json"
                a = JSONViewer(root, filename)
                root.geometry("600x800")
                root.configure(bg="gray20")
                root.mainloop()
    except Exception as e:
        print(e)

    # TetraLogger
    try:
        if choice == 11:
            if __name__ == '__main__':
                root = tk.Tk()
                root.title("Image cropper and assigner")
                a = ImageCropper(root,
                                 'tetra crops/reward artifacts.png',
                                 "tetra crops/tetra item names.txt",
                                 97, 8, 46, 55,
                                 "Results/ItemsAndImagesTetraRewards.json")
                root.configure(bg="gray20")
                root.mainloop()

        elif choice == 12:
            if __name__ == '__main__':
                root = tk.Tk()
                root.title("Image cropper and assigner")
                a = ImageCropper(root,
                                 'tetra crops/bank artifacts.png',
                                 "tetra crops/tetra item names.txt",
                                 45, 21, 44, 44,
                                 "Results/ItemsAndImagesTetraBank.json")
                root.configure(bg="gray20")
                root.mainloop()

        elif choice == 13:
            sort_rewards_and_bank()

        elif choice == 14:
            if __name__ == '__main__':
                root = tk.Tk()
                root.title("JSONViewer")
                filename = "JSON images/ItemsAndImagesTetra.json"
                a = JSONViewer(root, filename)
                root.geometry("600x800")
                root.configure(bg="gray20")
                root.mainloop()

        elif choice == 15:
            if __name__ == '__main__':
                root = tk.Tk()
                root.title("Image cropper and assigner")
                a = ImageCropper(root,
                                 "tetra crops/fiveitems artifacts.png",
                                 "tetra crops/tetra item names.txt",
                                 1, 5, 44, 44,
                                 "Results/ItemsAndImagesTetraFive.json")
                root.configure(bg="gray20")
                root.mainloop()

        elif choice == 16:
            blue_to_tan_tetras()

        elif choice == 17:
            values_tetra()

        elif choice == 18:
            remove_underscores('/tetra images')

        elif choice == 19:
            duplicate_remover()

        elif choice == 20:
            if __name__ == '__main__':
                root = tk.Tk()
                root.title("JSONViewer")
                filename = "JSON images/ItemsAndImagesTetraLegacy.json"
                a = JSONViewer(root, filename)
                root.geometry("600x800")
                root.configure(bg="gray20")
                root.mainloop()
    except Exception as e:
        print(e)

    # CrystalLogger
    try:
        if choice == 22:
            values_crystal()

        elif choice == 23:
            if __name__ == '__main__':
                root = tk.Tk()
                root.title("Image cropper and assigner")
                a = ImageCropper(root,
                                 "crystal crops/rewards crystal.png",
                                 "crystal crops/crystalitems.txt",
                                 9, 8, 46, 55,
                                 "Results/ItemsAndImagesCrystalRewards.json")
                root.configure(bg="gray20")
                root.mainloop()

        elif choice == 24:
            if __name__ == '__main__':
                root = tk.Tk()
                root.title("Image cropper and assigner")
                a = ImageCropper(root,
                                 "crystal crops/trade crystal.png",
                                 "crystal crops/crystalitems.txt",
                                 36, 4, 32, 47,
                                 "Results/ItemsAndImagesCrystalTrade.json")
                root.configure(bg="gray20")
                root.mainloop()

        elif choice == 25:
            sort_rewards_and_trade()

        elif choice == 26:
            duplicate_remover_crystal()

        elif choice == 27:
            if __name__ == '__main__':
                root = tk.Tk()
                root.title("JSONViewer")
                filename = "crystal crops/ItemsAndImagesCrystalOneList.json"
                a = JSONViewer(root, filename)
                root.geometry("600x800")
                root.configure(bg="gray20")
                root.mainloop()

        elif choice == 28:
            blue_to_tan_crystal()

        elif choice == 29:
            if __name__ == '__main__':
                root = tk.Tk()
                root.title("JSONViewer")
                filename = "crystal crops/ItemsAndImagesCrystalLegacyOneList.json"
                a = JSONViewer(root, filename)
                root.geometry("600x800")
                root.configure(bg="gray20")
                root.mainloop()

        elif choice == 30:
            remove_underscores('/crystal images')

    except Exception as e:
        print(e)
