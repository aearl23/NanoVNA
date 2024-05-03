from guizero import App, MenuBar, Box, Picture, ListBox, Text, PushButton, Combo
from guizero import *
import pandas as pd
import tkinter as tk 
import webbrowser
from tkinter import ttk
import threading 

#GPS imports 
import time
import board
import serial
import busio
import adafruit_gps
import csv
import requests
import asyncio 

#NanoSaver Imports 
import NanoVNASaver
from nanoVNA_utils import connect_to_nano_vna, set_frequency_parameters, set_marker_parameters, get_s21_gain


#gps_simple: run every 5 seconds and writes to file 
#main: pulls data from txt file and returns the most recent 

#global variables to store lat and lng 
latest_latitude = None 
latest_longitude = None
    
#constantly read gps data    
async def gps_worker():
    global latest_latitude, latest_longitude
        #function that wirtes gps data to gps_data.txt
        # Create a serial connection for the GPS connection using default speed
    uart = serial.Serial("/dev/serial0", baudrate=9600, timeout=3000)

        # Create a GPS module instance.
    gps = adafruit_gps.GPS(uart, debug=False)
         # Use UART/pyserial
        
    gps.send_command(b"PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
    gps.send_command(b"PMTK220,1000")

        # Main loop runs forever printing the location, etc. every second.
    last_print = time.monotonic()
    while True:
            # Make sure to call gps.update() every loop iteration and at least twice
            # as fast as data comes from the GPS unit (usually every second).
            # This returns a bool that's true if it parsed new data (you can ignore it
            # though if you don't care and instead look at the has_fix property).
        gps.update()
            # Every second save current location details to global variables if there's a fix.
        current = time.monotonic()
        if current - last_print >= 1.0:
            last_print = current
            if gps.has_fix:
                latest_latitude = gps.latitude
                latest_longitude = gps.longitude
                print("=" * 40)  # Print a separator line.
                print("Fix timestamp: {}/{}/{} {:02}:{:02}:{:02}".format(
                    gps.timestamp_utc.tm_mon,  # Grab parts of the time from the
                    gps.timestamp_utc.tm_mday,  # struct_time object that holds
                    gps.timestamp_utc.tm_year,  # the fix time.  Note you might
                    gps.timestamp_utc.tm_hour,  # not get all data like year, day,
                    gps.timestamp_utc.tm_min,  # month!
                    gps.timestamp_utc.tm_sec,
                ))
                print("Latitude: {0:.6f} degrees".format(gps.latitude))
                print("Longitude: {0:.6f} degrees".format(gps.longitude))
                print("Precise Latitude: {:.0f}.{:04.4f} degrees".format(
                    gps.latitude_degrees, gps.latitude_minutes
                ))
                print("Precise Longitude: {:.0f}.{:04.4f} degrees".format(
                    gps.longitude_degrees, gps.longitude_minutes
                ))     
            else:
                print("Waiting for fix...")
    await asyncio.sleep(1)
                # We have a fix! (gps.has_fix is true)
                # Print out details about the fix like location, date, etc.
            
#start gps thread on GUI start   

#Dr. Bean - try using asynch or other method, avoid threading. Schedule office hours for extended hours 
#Look in to applying async methods
    
    
scan_count = 0 
scan_data = {
     'Number':[],
     'Evaluation':[],
     'Latitude':[],
     'Longitude':[]
    }


#set up functions that will enable reading of NanoVNA data

#steps: 1) connect to VNA  2) Set MHz or Markers (set to 600 - 700 MHz) 3) Marker2 set at 650 MHz 4) functions defining evaluation criteria given S21 gain data 
#if water is present, S21 gain falls below 60, use as benchmark 

def find_vna():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "04b4:0008" in port.usb_info():
            return port.device 
        return None

def connect_vna(button): 
    global vna 
    vna_port = find_vna()
    baudrate = 115200
    vna = connect_to_nano_vna("serial", "/dev/ttyUSBO")

    if vna: 
        #change button text to connected 
        connect_button.text = "Connected"

        #Desired frequency hard coded into the parameters 
        set_frequency_parameters(vna, 600000, 700000, 101)

        #ideal location of marker 
        set_marker_parameters(vna, 1, 6500000)

        #grab s21 value 
        s21_gain = get_s21_gain(vna)


def evaluate(s21_gain): 
        if s21_gain < 60: 
            evaluation = "Water detected"
            return evaluation 
        else: 
            evaulation = "No water detected"
            return evaluation 
    
    
async def run_gui_program():
        
  
    def log(): 
        global latest_latitude, latest_longitude, scan_count, scan_data
        scan_count = len(scan_data['Number']) + 1 
        new_scan = {
            'Number': scan_count,
            'Evaluation': evaluate(),
            'Latitude': latest_latitude,
            'Longitude':latest_longitude
        }
        for key, value in new_scan.items():
            scan_data[key].append(value)
    def scan():
        #placeholder for Doctor Miseo's code
        pass

    def create_scan_action():
        # Action for the "Create Scan" button
        picture.hide()
        welcome_message.hide()
        show_page(create_scan_screen)
        
    def view_data_action():
        # Action for the "View Data" button
        picture.hide()
        welcome_message.hide()
        show_page(view_data_screen)
        display_table()

    def display_table():
        # Create a new tkinter Frame to hold the table
        table_frame = tk.Frame(view_data_screen.tk)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        # Create a treeview widget
        tree = ttk.Treeview(table_frame, columns=('Scan Number','Evaluation','Latitude','Longitude'), show = 'headings')
        tree.heading('Scan Number', text = 'Scan count')
        tree.heading('Evaluation', text = 'Evaluation')
        tree.heading('Latitude', text = 'Latitude')
        tree.heading('Longitude', text = 'Longitude')
        tree.pack(fill=tk.BOTH, expand=1)

        #grab count and evaluation data
        for index in range(len(scan_data['Number'])):
            scan_number = scan_data['Number'][index]            
            evaluation = scan_data['Evaluation'][index]
            Latitude = scan_data['Latitude'][index]
            Longitude = scan_data['Longitude'][index]
            tree.insert("","end", values=(scan_number, evaluation, Latitude, Longitude))
        #grab data from gps 

        
    def gps_action():
        # Action for the "GPS" button
        picture.hide()
        welcome_message.hide()
        show_page(gps_screen)
    
    def gather_data_to_export():
        data_to_export = []
        for index in range(len(scan_data['Number'])):
            latitude = scan_data['Latitude'][index]
            longitude = scan_data['Longitude'][index]
            data_to_export.append((latitude, longitude))
        export_data_to_map(data_to_export)    
    
    def export_data_to_map():
        #step 1, login and return the session ID

        def login(email, password):
            print("attempting login....")
            url = "https://maps.co/api/userLogIn"
            data = {
                "userEmail": email,
                "userPassword": password
            }

            try:
                response = requests.post(url, json=data)
                print("response content:", response.content)
                response_json = response.json()
                
                if response_json.get("success") == 1:
                    session_id = response_json["USER"]["sessionID"]
                    print("Login successful. Session ID:", session_id)
                    return session_id
                else:
                    print("Login failed:", response_json.get("message"))
                    return None
            except Exception as e:
                print("An error occurred during login:", e)
                return None

        session_id = login("aaronearl7@gmail.com", "ae030456")
        print("Session ID:", session_id)


        #step 2, function to get the layers 

        def get_layers(session_id):
            print("Getting list of layers....")
            url = "https://maps.co/api/userGetLayers"
            headers = {
                "Cookie": f"sessionID={session_id}"
            }

            try:
                response = requests.get(url, headers=headers)
                print("response content:", response.content)
                response_json = response.json()
                
                if response_json.get("success") == 1:
                    layers = response_json.get("Layers", {})
                    print("List of layers:", layers)
                    return layers
                else:
                    print("Failed to get list of layers:", response_json.get("message"))
                    return None
            except Exception as e:
                print("An error occurred while getting list of layers:", e)
                return None

        session_id = "65e20dc1411db070603766ige33a641"
        layers = get_layers(session_id)


        #step 3, Manually add locations to layer 

        def add_location_to_layer(session_id, layer_id, layer_name, latitude, longitude):
            print("Adding location to layer....")
            url = "https://maps.co/api/layerLocationAdd"
            data = {
                "layerID": layer_id,
                "layerName": layer_name,
                "lat": latitude,
                "lng": longitude
            }
            headers = {
                "Cookie": f"sessionID={session_id}"
            }

            try:
                response = requests.post(url, json=data, headers=headers)
                print("Response content:", response.content)
                response_json = response.json()

                if response_json.get("success") == 1:
                    print("Location added successfully to layer.")
                else:
                    print("Failed to add location to layer:", response_json.get("message"))
            except Exception as e:
                print("An error occurred while adding location to layer:", e)

        #Usage  - Set to continuously read the data from the data table 

        session_id = "65e20dc1411db070603766ige33a641"
        layer_id = "65e2139f6e47e308984963abz393654"
        layer_name = "rasp_pi gps test v.1"

        #Map the same data displayed to the data table 
        for index in range(len(scan_data['Number'])):
            latitude = scan_data['Latitude'][index]
            longitude = scan_data['Longitude'][index]

        #Call the function to add data to map layer 
        add_location_to_layer(session_id, layer_id, layer_name, latitude, longitude)


        url = "https://maps.co/gis/"
        webbrowser.open(url) 


    def home_action():
        # Action for the "Home" button  
        picture.show()
        welcome_message.show()
        show_page(home_screen)

    def about_action():
        # Action for the "About" button
        picture.hide()
        welcome_message.hide()
        show_page(about_screen)

    def show_page(page):
        # Hide all pages
        for p in all_pages:
            p.hide()
        # Show the selected page
        page.show()
        
        
    def do_this_when_closed():
        if app.yesno("Close", "Are you sure you want to close the app?"):
            app.destroy()



    #GUI Visaul setup for buttons, formatting, and pages 
    
    app=App(title="Corn Stalk Measurment Device", width=800, height=450)
    app.bg = "white"
    app.when_start = start_gps_thread
    app.when_closed = do_this_when_closed
        

    #Menu bar
    navigation_box = Box(app, width="fill", align="bottom", layout="grid")
    button_width = 17
    button_height = 3 
    button_margin = 10
    # Add large buttons for navigation
    home_button = PushButton(navigation_box, text="Home", command=home_action, width=button_width, height=button_height, grid=[0,0])
    create_scan_button = PushButton(navigation_box, text="Create Scan", command=create_scan_action, width=button_width, height=button_height, grid=[1,0])
    view_data_button = PushButton(navigation_box, text="View Data", command=view_data_action, width=button_width, height=button_height, grid=[2,0])
    gps_button = PushButton(navigation_box, text="GPS", command=gps_action, width=button_width, height=button_height, grid=[3,0])
    about_button = PushButton(navigation_box, text="About", command=about_action, width=button_width, height=button_height, grid=[4,0])

    # Home screen with an image
    home_screen = Box(app, width="fill", align="top")
    picture = Picture(home_screen, image="channels4_profile.jpg", grid=[4,4])
    welcome_message = Text(home_screen, text="Welcome to the Corn Stalk Measurement Device")

    # Home screen
    home_screen = Box(app, width="fill", align="top")
    # Add contents to the home screen
    home_text = Text(home_screen, text="Home Page", size=20)

    # Create scan screen
    create_scan_screen = Box(app, width="fill", align="top", visible=False)
    log_button = PushButton(create_scan_screen, text="Log Data to Table", command=log, height=button_height, width=button_width, grid=[3,1])
    scan_button = PushButton(create_scan_screen,text="Scan Stalk", command=scan, height=button_height, width=button_width, grid=[3,2])
    connect_button = PushButton(create_scan_screen, text="Connect to VNA", command=connect_vna, height=button_height, width=button_width, grid=[3,3])
    instructions = TextBox(create_scan_screen, grid=[3,0], text="Instructions: To being a scan, press the SCAN Button and follow on screen prompts. After the desired amount of scans have been completed, press the LOG button to Log scan and gps data to the tabel", width="fill")
    Evaluation = Box(create_scan_screen, text="Pass/Fail placeholder")
    scan_data = Box(create_scan_screen, text="scan results placeholder")
    # Add contents to the create scan screen
    
    
    # View data screen
    def clear_table():
        tree.delete(*tree.get_children())

    view_data_screen = Box(app, width="fill", align="top", visible=False)
    clear_button = PushButton(view_data_screen, text="clear table", command=clear_table, grid=[0,0])
    # Add contents to the view data screen

    # GPS screen
    gps_screen = Box(app, width="fill", align="top", visible=False)
    map_button = PushButton(gps_screen, text="Export data to map", command=export_data_to_map, height=button_height, width=button_width, grid=[3,1])
    coordinate_box = Box(gps_screen, align="left")
    lat = Text(coordinate_box, text="Current Latitude:" + int(latest_latitude))
    lng = Text(coordinate_box, text="Current Longitude:" + int(latest_longitude))
    # Add contents to the GPS screen

    # About screen
    about_screen = Box(app, width="fill", align="top", visible=False)
    # Add contents to the about screen
    about_text = Text(about_screen, text="About Page", size=20)
    about_information = TextBox(about_screen, text="The Corn Stalk Integration Device is a BYU Technology Transfer prototype relating to current research by BYU professors Cook and Mazzeo. The device eneables users to perform impedance testing on corn stalks to evaluate plant health. The device is equiped with GPS to track the location of the corn plant with its attributes that result from the scan.", width ="fill", height=5, multiline=True, grid=[0,1])

    # List of all pages
    all_pages = [home_screen, create_scan_screen, view_data_screen, gps_screen, about_screen]

    # Initially show the home screen
    show_page(home_screen)
    app.display()

def start_gps_worker():
    asyncio.run(gps_worker())

def main():
    gps_thread = threading.Thread(target=start_gps_worker)
    gps_thread.start()
    asyncio.run(run_gui_program())

if __name__ == "__main__":
    main()
