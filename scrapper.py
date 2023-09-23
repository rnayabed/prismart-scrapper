#!/usr/bin/env python3

'''
A very poor and hastly written script to scrap paints information from 
the Fast and Fluid Dispenser Android App (PrismaRT) and save it to a database

Written by Debayan Sutradhar (@rnayabed)
Licensed to GPLv3
'''

import subprocess
import PIL
import enum
import pytesseract as pt
import io
import time
import chime
import pathlib
import datetime
import psycopg2
import traceback
import sys

class ScreenType(enum.Enum):
    HOME = 1
    SEARCH_HOME = 2
    SEARCH_COLOUR = 3
    SEARCH_BASE = 4
    SEARCH_COLLECTION = 5
    DISPENSE_FINAL = 6
    ADJUST_FORMULA = 7
    INVALID = 8

# Get screenshot and return raw data
def take_screenshot():
    r = subprocess.run(['adb' , 'exec-out', 'screencap', '-p'], stdout=subprocess.PIPE)
    return io.BytesIO(r.stdout)

def touch_screen(x, y):
    subprocess.run(['adb' , 'shell', 'input', 'tap' , str(x), str(y)])
    touch_sleep()

def touch_and_hold_screen(x, y):
    subprocess.run(['adb' , 'shell', 'input', 'motionevent', 'DOWN', str(x), str(y)])
    touch_sleep()
    subprocess.run(['adb' , 'shell', 'input', 'motionevent', 'UP', str(x), str(y)])
    touch_sleep()

def scroll_screen_full():
    subprocess.run(['adb', 'shell', 'input', 'roll', '0', '13'])
    touch_sleep()

def scroll_screen_full_alt():
    subprocess.run(['adb', 'shell', 'input', 'swipe', '600', '1900', '600', '225', '3000'])
    touch_sleep()

def go_back():
    touch_screen(332, 1955)
    touch_sleep()

def touch_sleep():
    time.sleep(0.5)

screen_type_checks = {
    ScreenType.HOME : [
        [
            (45, 228, 414, 321),
            'Standard Dispense'
        ]
    ],
    
    ScreenType.SEARCH_HOME : [
        [
            (36, 771, 740, 846),
            'Search results by color, product & collection'
        ]
    ],

    ScreenType.SEARCH_COLOUR : [
        [
            (81, 171, 684, 243),
            'Search for color name or color code'
        ],
        [
            (390, 78, 789, 144),
            'Standard Dispense'
        ]
    ],

    ScreenType.SEARCH_BASE : [
        [
            (81, 168, 723, 225),
            'Search for product name or base code'
        ]
    ],

    ScreenType.SEARCH_COLLECTION : [
        [
            (81, 168, 723, 225),
            'Search for collection name'
        ]
    ],
    
    ScreenType.ADJUST_FORMULA : [
        [
            (426, 57, 768, 114),
            'Adjust Formula'
        ]
    ],

    ScreenType.DISPENSE_FINAL : [
        [
            (528, 1842, 915, 1896),
            'START DISPENSING'
        ]
    ],  
}
    
def get_screen_type():
    return get_screen_type_img(PIL.Image.open(take_screenshot()))

def get_screen_type_img(img):
    for m, l in screen_type_checks.items():
        for e in l:
            if e[1] in pt.image_to_string(img.crop(e[0])):
                return m
    
    return ScreenType.INVALID

class LogColourType(enum.Enum):
    ADDED = 1
    IGNORED = 2
    IGNORED_BECAUSE_ALREADY_ADDED = 3
    ADDED_BUT_RECTIFIED = 4
    SILENT_IGNORE = 5

    def get_ui_value(type):
        match type:
            case LogColourType.ADDED: return "added"
            case LogColourType.IGNORED: return "ignored"
            case LogColourType.IGNORED_BECAUSE_ALREADY_ADDED: return "ignored_because_already_added"
            case LogColourType.ADDED_BUT_RECTIFIED: return "added_but_rectified"
            case LogColourType.SILENT_IGNORE: return "silent_ignore"

def log_colour(base_code, colour_code, collection, type: LogColourType):
    global log_folder_path
    pathlib.Path(log_folder_path).mkdir(exist_ok=True, parents=True)

    f = open(f'{log_folder_path}/{LogColourType.get_ui_value(type)}.txt', 'a+')
    f.writelines([f'base_code: {base_code}\n', f'colour_code: {colour_code}\n', f'collection: {collection}\n','\n'])
    f.close()

def register_paint_details(img):
    lines = pt.image_to_string(img).replace('\n\n','\n').split('\n')

    colour_name = None
    colour_code = None
    collection = None
    base_name = None
    base_code = None

    #component_mode = False
    #component_mode_done = False
    #components_temp = []
    #comp_two_mode = True
    #comp_mode_selected = False


    components = {}

    print('Lines::', lines)
    
    for line_num in range(len(lines)):
        if 'Formula Name' in lines[line_num]:
            colour_name = lines[line_num + 1].strip().upper()
        elif 'Color Code' in lines[line_num]:
            colour_code = lines[line_num].replace('Color Code', '').replace(':', '').strip().upper()
        elif 'Collection' in lines[line_num]:
            collection = lines[line_num].replace('Collection', '').replace(':', '').strip().upper()
        elif 'Product Name' in lines[line_num]:
            base_name = lines[line_num + 1].replace(' >', '').strip().upper()
        elif 'Base' in lines[line_num]:
            base_code = lines[line_num + 1].replace(' >', '').strip().upper()
        elif lines[line_num].strip().endswith(' MI'):
            txt = lines[line_num]
            mi_count = txt.count(' MI')

            if mi_count == 1:
                components[lines[line_num - 1].strip().upper()] = float(txt.replace(' MI', '').strip())
            elif mi_count == 2:
                ly = txt.strip().replace(' MI', '').split(' ')
                lx = lines[line_num - 1].strip().upper().split(' ')

                components[lx[0]] = float(ly[0])
                components[lx[1]] = float(ly[1])


        '''
        elif not component_mode_done:
            txt = lines[line_num]

            if comp_mode_selected:
                if not comp_two_mode:
                    if txt.count(' MI') == 1:
                        c_name = lines[line_num - 1].strip().upper()
                        c_quant = float(txt.strip().upper().replace(' MI', ''))
                        components[c_name] = c_quant
                else:
                    if len(txt.strip()) != 0:
                        if 'Comments :' in txt:
                            component_mode = False
                            component_mode_done = True
                        else:
                            c = txt.strip().upper().replace(' MI', '').split(" ")
                            for cc in c:
                                components_temp.append(cc)
            else:
                if 'Components :' in txt:
                    component_mode = True

                    # Decide mode_type
                    comp_two_mode = False
                    for ln in range(line_num,len(lines)):
                        if lines[ln].count(' MI') == 2:
                            comp_two_mode = True
                            break

                    print('TWO MODE? ', comp_two_mode)
                    comp_mode_selected = True
        '''
    
    '''
    if comp_two_mode:
        components = {}
        print('components_temp', components_temp)

        for i in range(0, len(components_temp)):
            # Two or One count
            if components_temp[i].count('.') == 2:
                # Two count
                ly = components_temp[i].split(' ')
                lx = components_temp[i - 1].split(' ')
                components[lx[0]] = float(ly[0])
                components[lx[1]] = float(ly[1])
            else:
                components[lx[0]] = float(components_temp[i])

        
        # Rare mode
        rare_mode = True
        for i in range(0, len(components_temp)):
            if '.' in components_temp[i] and i % 2 == 0: 
                #print('Rare mode broken! ', i, components_temp[i])
                rare_mode = False
                break
            if '.' not in components_temp[i] and i % 2 != 0: 
                #print('Rare mode broken! xx ', i, components_temp[i]) 
                rare_mode = False
                break

        if rare_mode:
            for i in range(0, len(components_temp), 2):
                components[components_temp[i]] = float(components_temp[i + 1])
        else:
            # Normal mode
            for i in range(0, len(components_temp), 4):
                # either one mode or two mode
                if ('.' in components_temp[i + 1]):
                    # One mode
                    components[components_temp[i]] = float(components_temp[i + 1])
                else:
                    # Two mode
                    components[components_temp[i]] = float(components_temp[i + 2])
                    components[components_temp[i + 1]] = float(components_temp[i + 3])
        
    '''

    return (base_code, base_name, colour_code, colour_name, components, collection)

db_con = None
db_cur = None
def db_connect(username, password, db_name, host):
    global db_con
    db_con = psycopg2.connect(database=db_name, user=username, password=password, host=host)

    global db_cur
    db_cur = db_con.cursor()

def db_setup():
    pass

'''
Create syntax

-- colourant
CREATE TABLE colourant (
    id TEXT NOT NULL PRIMARY KEY,
    name TEXT
);

-- base
CREATE TABLE base (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL,
    name TEXT NOT NULL
);

-- collection
CREATE TABLE collection(
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

-- colours
CREATE TABLE colour(
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL,
    name TEXT NOT NULL, 
    collection INTEGER NOT NULL,
    base INTEGER NOT NULL,
    colourants TEXT[] NOT NULL, 
    colourants_quantity REAL[] NOT NULL, 
    
    CONSTRAINT fk_base
        FOREIGN KEY (base)
            REFERENCES base(id),
    CONSTRAINT fk_collection
        FOREIGN KEY (collection)
            REFERENCES collection(id)
);



              Table "public.base"
 Column | Type | Collation | Nullable | Default 
--------+------+-----------+----------+---------
 id     | text |           | not null | 
 name   | text |           | not null | 
Indexes:
    "base_pkey" PRIMARY KEY, btree (id)
Referenced by:
    TABLE "colour" CONSTRAINT "fk_base" FOREIGN KEY (base) REFERENCES base(id)



                            Table "public.collection"
 Column |  Type   | Collation | Nullable |                Default                 
--------+---------+-----------+----------+----------------------------------------
 id     | integer |           | not null | nextval('collection_id_seq'::regclass)
 name   | text    |           | not null | 
Indexes:
    "collection_pkey" PRIMARY KEY, btree (id)
    "collection_name_key" UNIQUE CONSTRAINT, btree (name)
Referenced by:
    TABLE "colour" CONSTRAINT "fk_collection" FOREIGN KEY (collection) REFERENCES collection(id)



                                   Table "public.colour"
       Column        |  Type   | Collation | Nullable |              Default               
---------------------+---------+-----------+----------+------------------------------------
 id                  | integer |           | not null | nextval('colour_id_seq'::regclass)
 code                | text    |           | not null | 
 name                | text    |           | not null | 
 collection          | integer |           | not null | 
 base                | text    |           | not null | 
 colourants          | text[]  |           | not null | 
 colourants_quantity | real[]  |           | not null | 
Indexes:
    "colour_pkey" PRIMARY KEY, btree (id)
Foreign-key constraints:
    "fk_base" FOREIGN KEY (base) REFERENCES base(id)
    "fk_collection" FOREIGN KEY (collection) REFERENCES collection(id)



            Table "public.colourant"
 Column | Type | Collation | Nullable | Default 
--------+------+-----------+----------+---------
 id     | text |           | not null | 
 name   | text |           |          | 
Indexes:
    "colourant_pkey" PRIMARY KEY, btree (id)
'''

# TODO: Configure database if does not exist

def db_check_colour_exists(base_code, base_name, colour_code, colour_name, collection):
    db_cur.execute("SELECT id from collection WHERE name=%s", (collection,))
    xx = db_cur.fetchall()
    if len(xx) == 0: return False
    collection_id = xx[0]

    db_cur.execute("SELECT id FROM base WHERE code=%s AND name=%s", (base_code, base_name))
    yy = db_cur.fetchall()
    if len(yy) == 0: return False
    base_id = yy[0]

    db_cur.execute("SELECT * FROM colour WHERE code=%s AND name=%s AND collection=%s AND base=%s;", 
        (colour_code, colour_name, collection_id, base_id))
    return True if len(db_cur.fetchall()) > 0 else False
    

def db_save(base_code, base_name, colour_code, colour_name, components, collection, was_rectified):
    global db_cur
    global db_con

    # add collection
    db_cur.execute("INSERT INTO collection(name) VALUES (%s) ON CONFLICT(name) DO NOTHING;", (collection,))
    db_cur.execute("SELECT id from collection WHERE name=%s;", (collection,))
    collection_id = db_cur.fetchone()[0]
    
    # add base
    db_cur.execute("SELECT id FROM base WHERE code=%s AND name=%s;", (base_code, base_name))
    xy = db_cur.fetchall()
    base_id=-1
    if len(xy) == 0:
        db_cur.execute("INSERT INTO base(code, name) VALUES (%s, %s);", (base_code, base_name))
        db_cur.execute("SELECT id FROM base WHERE code=%s AND name=%s;", (base_code, base_name))
        base_id = db_cur.fetchone()[0]
    else:
        print('BASE EXIST!', xy[0])
        base_id = xy[0]
    
    print('base_id', base_id)

   
    

    colourants_l = []
    colourants_quantity_l = []
    for c, d in components.items():
        # Add colourant
        db_cur.execute("INSERT INTO colourant(id) VALUES (%s) ON CONFLICT(id) DO NOTHING;", (c,))
        colourants_l.append(c)
        colourants_quantity_l.append(d)

    db_cur.execute("SELECT * FROM colour WHERE code=%s AND name=%s AND collection=%s AND base=%s;", 
        (colour_code, colour_name, collection_id, base_id))
    if len(db_cur.fetchall()) > 0:
        print('Already exists! Ignored')
        log_colour(base_code, colour_code, collection, LogColourType.IGNORED_BECAUSE_ALREADY_ADDED)
    else:
        # add colour with components, base (unique) and collection (unique)
        print("Saved to database!")
        db_cur.execute("INSERT INTO colour(code, name, collection, base, colourants, colourants_quantity) \
            VALUES (%s, %s, %s, %s, %s, %s);", 
            (colour_code, colour_name, collection_id, base_id, colourants_l, colourants_quantity_l))
        log_colour(base_code, colour_code, collection, LogColourType.ADDED_BUT_RECTIFIED if was_rectified else LogColourType.ADDED)

    db_con.commit()
    
def db_disconnect():
    global db_con
    global db_cur

    if db_con is None or db_cur is None: return

    db_cur.close()
    db_con.close()

def get_q_index(list):
    q_index = 0
    for i in range(len(list)):
        if list[i] == 'Q': 
            q_index = i
            break
    return q_index

class AppCrashed(Exception):
    pass

def register_from_current_colour_pallete():

    colour_number = 0

    img = None
    while True:
        img = PIL.Image.open(take_screenshot()) 
        if get_screen_type_img(img) != ScreenType.SEARCH_COLOUR:
            input("Please go to colour selection screen from colour pallete! Then press enter")
            continue
        break

    global collection_name
    collection_name = pt.image_to_string(img.crop((102, 69, 771, 138))).replace('@', '') \
            .replace('|', '') \
            .replace(' po', '') \
            .replace('\n','') \
            .strip().upper()

    gap = 170
    max_per_screen = 10
    ref_loc = (436, 326)
    
    old_colour_data = None
    new_colour_data = list(filter(lambda x: x != '', pt.image_to_string(PIL.Image.open(take_screenshot())).split('\n')))


    while old_colour_data != new_colour_data:
        colour_index = 0

        for l in range(get_q_index(new_colour_data) + 1, len(new_colour_data), 2):
            

            if l == len(new_colour_data) - 1: break
            xlenxx = len(new_colour_data[l].strip())
            xlenxx_next = len(new_colour_data[l+1].strip())
            if (xlenxx < 2 or xlenxx_next < 2) or (xlenxx == 0 or xlenxx_next == 0): continue
                   
            colour_name = new_colour_data[l].strip().upper()
            colour_code = new_colour_data[l+1].strip().upper()

            print()
            print('===========')
            print('Enter new colour section', colour_name, ':', colour_code)

            loc = list(ref_loc)
            loc[1] += colour_index * gap
            touch_screen(loc[0], loc[1])
            colour_index+=1
            
            while (get_screen_type() != ScreenType.SEARCH_BASE):
                chime.warning()
                input("WARNING: Screen not in base search. Please fix. Enter to continue")

            old_base_data = None
                                    
            new_base_data = list(filter(lambda x: len(x.strip()) > 0, pt.image_to_string(PIL.Image.open(take_screenshot())).split('\n')))


            while old_base_data != new_base_data:
                base_index = 0

                print()
                print('new_base_data')
                print(new_base_data)
                print('!!!===!!!')
                print()

                print()

                for l in range(get_q_index(new_base_data) + 1, len(new_base_data), 2):

                    if l == len(new_base_data) - 1: break
                    lenxx = len(new_base_data[l].strip())
                    lenxx_next = len(new_base_data[l+1].strip())
                    if (lenxx < 2 or lenxx_next < 2) or (lenxx == 0 or lenxx_next == 0): continue
                   

                    base_name = new_base_data[l].strip().upper()
                    base_code = new_base_data[l+1].strip().upper()

                    base_loc = list(ref_loc)
                    base_loc[1] += base_index * gap
                    base_index+=1
                    colour_number+=1

                    if db_check_colour_exists(base_code, base_name, colour_code, colour_name, collection_name):
                        print(f"Colour {base_name}, {base_code}, {colour_code}, {colour_name} already exists!")
                        log_colour(base_code, colour_code, collection_name, LogColourType.IGNORED_BECAUSE_ALREADY_ADDED)
                        continue

                    touch_screen(base_loc[0], base_loc[1])

                    touch_sleep()
                    touch_screen(1143, 87)

                    print(f'Trying to enter {base_name}, {base_code}, {colour_name}, {colour_code}')


                    il_ignore = False
                    while True:
                        # get data

                        img = None
                        while True:
                            img = PIL.Image.open(take_screenshot())
                            if get_screen_type_img(img) == ScreenType.ADJUST_FORMULA: break
                            chime.warning()
                            print("WARNING: Screen not in adjust formula. Please fix. Enter to continue")
                            if silent_ignore:
                                raise AppCrashed
                            else:
                                input()


                        try:
                            final_base_code, final_base_name, final_colour_code, final_colour_name, final_components, final_collection = register_paint_details(img)
                            break
                        except:
                            traceback.print_exc()
                            print('Failed to register paint_details!')
                            chime.error()

                            choice = 'sdf'

                            if silent_ignore:
                                print('ignoring')
                                choice = 'I'
                            else:
                                choice = input('Retry [anything], Ignore this and continue [I] : ')

                            if choice == 'I':
                                print('Skipping ...')
                                log_colour(base_code, colour_code, collection_name, LogColourType.IGNORED)
                                go_back()
                                go_back()
                                print()
                                il_ignore = True
                                break
                    
                    if il_ignore: continue

                    print()
                    print('===New entry details===')
                    print('Number: ', colour_number)
                    print('Base Code:', final_base_code)
                    print('Base Name:', final_base_name)
                    print('Colour Code:', final_colour_code)
                    print('Colour Name:', final_colour_name)
                    print('Components:', len(final_components), final_components)
                    print('Collection:', final_collection)

                    confirm_input = False
                    ignore = False
                    was_rectified = False

                    if final_colour_name != colour_name:
                        chime.warning()
                        confirm_input = True
                        print("WARNING! Mismatch colour name (Org: '"+colour_name+"'. Screen: '"+final_colour_name+"'")
                    
                    if final_colour_code != colour_code:
                        chime.warning()
                        confirm_input = True
                        print("WARNING! Mismatch colour code (Org: '"+colour_code+"'. Screen: '"+final_colour_code+"')")
                    
                    if final_base_name != base_name:
                        chime.warning()
                        confirm_input = True
                        print("WARNING! Mismatch base name (Org: '"+base_name+"'. Screen: '"+final_base_name+"')")
                    
                    if final_base_code != base_code:
                        if base_code.replace(' A)', '') == final_base_code:
                            base_code = base_code.replace(' A)','')
                            print('Fixed minor base code problem')
                        else:
                            chime.warning()
                            confirm_input = True
                            print("WARNING! Mismatch base code (Org: '"+base_code+"'. Screen: '"+final_base_code+"')")
                    
                    if final_collection != collection_name:
                        chime.warning()
                        confirm_input = True
                        print("WARNING! Mismatch base code (Org: '"+collection_name+"'. Screen: '"+final_collection+"')")
                    
                    if confirm_input:
                        if silent_ignore:
                            print("SILENT IGNORED")
                            print('Skipping ...')
                            log_colour(base_code, colour_code, collection_name, LogColourType.SILENT_IGNORE)
                            go_back()
                            go_back()
                            print()
                            continue
                        else:
                            input()
                

                    while confirm_input:
                        print()
                        print('===Verify details===')
                        print('Base Code:', final_base_code)
                        print('Base Name:', final_base_name)
                        print('Colour Code:', final_colour_code)
                        print('Colour Name:', final_colour_name)
                        print('Collection:', final_collection)
                        print('Components: ', final_components)
                        choice = input('Save and proceed? [S], Edit [E], Cancel and ignore [I] : ')
                        if choice == 'E':
                            print('Enter Base Code: ["'+ final_base_code +'"]:')
                            user_base_code = input()
                            if (user_base_code != ''): final_base_code = user_base_code

                            print('Enter Base Name: ["'+ final_base_name +'"]:')
                            user_base_name = input()
                            if (user_base_name != ''): final_base_name = user_base_name

                            print('Enter Colour Code: ["'+ final_colour_code +'"]:')
                            user_colour_code = input()
                            if (user_colour_code != ''): final_colour_code = user_colour_code

                            print('Enter Colour Name: ["'+ final_colour_name +'"]:')
                            user_colour_name = input()
                            if (user_colour_name != ''): final_colour_name = user_colour_name

                            print('Enter Collection: ["'+ final_collection +'"]:')
                            user_collection = input()
                            if (user_collection != ''): final_collection = user_collection

                            # Components
                            while True:
                                try:
                                    print('Add components (separate by space and quantity in mL:)')
                                    user_components_temp = input()

                                    if user_components_temp != '':
                                        user_components_temp = user_components_temp.split(' ')
                                        for x in user_components_temp:
                                            xx = x.split(":")
                                            final_components[xx[0]] = float(xx[1])
                        
                                    print('Delete components (separate by space)')
                                    gg = input()
                                    if gg != '':
                                        for x in gg.split(' '):
                                            del final_components[x]

                                    break
                                except: 
                                    print('Invalid syntax! Try again')
                        

                        elif choice == 'S':
                            confirm_input = False
                            was_rectified = True
                        elif choice == 'I':
                            confirm_input = False
                            ignore = True

                    if ignore:
                        log_colour(base_code, colour_code, collection_name, LogColourType.IGNORED)                    
                    else:
                        db_save(final_base_code, final_base_name, final_colour_code,
                         final_colour_name, final_components, final_collection, was_rectified)

                    go_back()
                    go_back()
                    print()
                    
                print('Scrolling !!')
                scroll_screen_full_alt()
                old_base_data = new_base_data
                new_base_data = list(filter(lambda x: len(x.strip()) > 0, pt.image_to_string(PIL.Image.open(take_screenshot())).split('\n')))

            
            print('Same! no more to scroll! going back!')            
            go_back()

        scroll_screen_full()
        old_colour_data = new_colour_data
        new_colour_data = list(filter(lambda x: len(x.strip()) > 0, pt.image_to_string(PIL.Image.open(take_screenshot())).split('\n')))

def touch_type(text):
    subprocess.run(['adb', 'shell', 'input', 'text', text.replace(' ', '%s')])
    touch_sleep()

def start_app():
    # Home
    print('Press home')
    touch_screen(600, 1956)
    time.sleep(2)

    # Force stop PrismaRT
    print('Force stop PrismaRT')
    touch_and_hold_screen(714, 1131)
    time.sleep(1)
    touch_screen(600, 981)
    time.sleep(1)
    touch_screen(492, 1830)

    if 'misbehave' in pt.image_to_string(PIL.Image.open(take_screenshot())):
        touch_screen(720, 1101)

    time.sleep(2)

    print('Press home')
    touch_screen(600, 1956)
    time.sleep(2)

    # PrismaRT app
    print('Open PrismaRT')
    touch_screen(714, 1131)

    print('Wait for initialise')
    time.sleep(13)

    while True:
        img = PIL.Image.open(take_screenshot())
        if (get_screen_type_img(img) != ScreenType.HOME):
            input('Failed to launch app. Please manually do so.')
            continue
            
        if 'Ready' not in pt.image_to_string(img.crop((562, 160, 672, 199))):
            input('System not ready yet! You need to connect to the printer')
            continue
        
        break

    # Click standard dispense
    print('Open Standard Dispense')
    touch_screen(307, 464)
    time.sleep(2)

    # Click collection search
    print('Open Collection Search')
    touch_screen(540, 1047)
    time.sleep(1)

    # Move home shortcut (360, 1392)
    print('Move home shortcut')
    subprocess.run(['adb', 'shell', 'input', 'swipe', '360', '1392', '963', '1392', '300'])
    time.sleep(1)

    # Click text box
    print('Click input text box')
    touch_screen(111,206)
    
    global collection_name
    # Type collection name
    touch_type(collection_name)
    time.sleep(2)

    # Press on it
    touch_screen(555, 318)

    global db_cur
    db_cur.execute('SELECT id FROM collection WHERE NAME=%s;', (collection_name, ))
    collection_id = db_cur.fetchone()[0]

    db_cur.execute('SELECT DISTINCT name FROM colour WHERE collection=%s ORDER BY name DESC LIMIT 1;',
        (collection_id, ))
    top_colours_list = db_cur.fetchall()

    if len(top_colours_list) == 0:
        return

    colour_to_swipe_to = top_colours_list[0][0]

    print('Colour to scroll to', colour_to_swipe_to)

    while True:
        if colour_to_swipe_to in pt.image_to_string(PIL.Image.open(take_screenshot())):
            break

        scroll_screen_full()

log_folder_path = datetime.datetime.today().strftime("colour-logs/%Y-%m-%d %H:%M:%S/")
silent_ignore = True
collection_name = 'APL COLOURPALETTE'

if len(sys.argv) != 5:
    print("Invalid args")
    exit()

db_connect(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
chime.theme('big-sur')

def main():
    try:        
        if get_screen_type() != ScreenType.SEARCH_BASE:
            start_app()
        register_from_current_colour_pallete()
    except AppCrashed: # Will only trigger if silent_ignore is True, for now
        print('====APP CRASHED====')
        print('Restarting...')
        main()

try:
    main()
except KeyboardInterrupt:
    print()
    print('Interrupted mid execution!')
except:
    traceback.print_exc()
    print("Error occured! Aborting ...")

db_disconnect()
print(f'Data stored in {log_folder_path}')
