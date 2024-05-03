from gui_main import run_gui_program
from gui_main import gps_worker
import asycnio

async def main():
    #call the function to run the GUI program, start the gps thread in the background
    await asyncio.gather(
        run_gui_program(),
        gps_worker(),
    )    
    
if __name__ == "__main__":
    asyncio.run(main())
    