**TTO GUI/NanoVNA Saver software for the Corn Stalk Integration Device** 

Using source code from https://github.com/NanoVNA-Saver/nanovna-saver.git, the NanoVNA Saver is a multifunctional tool that will provide impedance measurements on materials placed between probes. 
The functionality of the program is as follows: 

- Read and display NanoVNA data via Raspi usb port
- Read and display GPS data using a GPS module via a serial connection 
- Analyze the NanoVNA data to track significant changes in the "S21 gain" parameter (energy passed through the material via the magnetic field) and detect (1) The presence of material between the probes and (2) Material characteristics such as the presence of water, hollow, or solid
- Log the data in a [Count, Evaluation, Latitude, Longitude] format
- Using a maps.io API, export coordinates to a map interface to show data points by latitude and longitude coordinates

GUI layout is optimized for a 800x450-5in Raspberry Pi 4B touchscreen. 


