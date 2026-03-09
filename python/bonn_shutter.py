'''
Docstring for repositories.COO-Workbench.controls-python.bonn_shutter
'''
import socket
from typing import Union, Tuple, Dict
import serial
import serial.tools.list_ports
from hardware_device_base import HardwareMotionBase

class BonnShutterCommands:
    '''
    Class for Bonn Shutter Commands
    bonn shutter 100m has 2 blades: A and B
    0 corresponds to blade A
    1 corresponds to blade B
    bonn shutter command format:
    <command> <value>\n
    '''
    # Command Constants
    OPEN = "os"
    CLOSE = "cs"
    STANDARD_CMDS = "s?"
    SPECIAL_CMDS = "s!"
    INTERACTIVE_MODE = "ia"         # value after->ex: "ia 1"
    BLADE_PROFILE_PARAMS = "sh"     # value after->ex: "sh 0/1" = A/B
    HOST_COM_PARAMS = "pp"
    MSEC_EXPOSE_TIME = "ex"         # value after->ex: "ex 500" for 500 milliseconds
    SHUTTER_IN_APERTURE = "ss"
    ACCEL_PARAMS = "ac"             # value after->ex: "ac 25000"
    CHECK_STATUS = "sv"             # value after->ex: "sv 0/1" = A/B
    FACTORY_RESET = "fd"


class BonnShutterController(HardwareMotionBase):
    '''
    BonnShutterController - USB and RJ45 control for Bonn Shutter devices.
       -100m model with 2 blades (A and B).
       -Communicates via socket (RJ45) or serial (USB FTDI).
    '''

    Cmds = BonnShutterCommands
    status = {0:None}
    state = {
        'is_open': False,
        'is_busy': False,
        'last_command': None,
        'shutter_state': None,
        'error_code': None,
        'connection_type': None,  # 'rj45' or 'usb'
        'is_connected': False
    }

    def __init__(self):
        '''Initialize the Bonn Shutter Controller.'''
        super().__init__()
        self.socket = None
        self.host = None
        self.port = None
        self.timeout = 5  # Default timeout in seconds
        self._usb_ports = []
        self.ftdi_ports = []
        self.dev = None

    def connect_rj45(self, host: str, port: int) -> None:
        '''Connect to the Bonn Shutter device.'''
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.timeout)
        try:
            self.socket.connect((self.host, self.port))
            self.state['connection_type'] = 'rj45'
            self.state['is_connected'] = True
        except socket.error as e:
            raise ConnectionError(f"Could not connect to {self.host}:{self.port} - {e}") from e

    def connect_usb(self, device_path: str) -> None:
        '''Connect to the Bonn Shutter device via USB (placeholder).'''
        try:
            self.dev = serial.Serial(port=device_path, baudrate=19200, bytesize=8,
                                         stopbits=1, parity=serial.PARITY_NONE)
            #clear input/output buffers and ensure connection is live
            self.dev.reset_input_buffer()
            self.dev.reset_output_buffer()
            self.state['connection_type'] = 'usb'
            self.state['is_connected'] = True
        except serial.SerialException as e:
            raise ConnectionError(f"Could not connect to USB device at {device_path} - {e}") from e

    def list_devices(self) -> None:
        '''List available USB devices (Bonn Shutter devices typically FTDI).'''
        self._usb_ports=serial.tools.list_ports.comports()

        for p in self._usb_ports:
            print('--------------------')
            print(f'p.pid: {p.pid}')
            print(f'p.device: {p.device}')
            print(f'p.name: {p.name}')
            print(f'p.description: {p.description}')
            print(f'p.manufacturer: {p.manufacturer}')
            if 'FTDI' in p.manufacturer:
                return self.ftdi_ports.append(p.device)
            return None

    def disconnect(self) -> None:
        '''Disconnect from the Bonn Shutter device.'''
        if self.socket:
            self.socket.close()
            self.socket = None
        if self.dev:
            self.dev.close()
            self.dev = None
        self.state['is_connected'] = False

    def send_command(self, command: str) -> list[str]:
        '''Send a command to the Bonn Shutter device and return the response.'''
        if not self.socket and not self.dev:
            raise ConnectionError("Not connected to the Bonn Shutter device.")

        try:
            if self.state['connection_type'] == 'rj45': # pylint: disable=R1705
                self.socket.sendall(command.encode('utf-8') + b'\r')
                return self._read_until_prompt_socket()
            elif self.state['connection_type'] == 'usb':
                self.dev.write((command.encode('utf-8') + b'\r'))
                return self._read_until_prompt_usb()
            raise ConnectionError("Unknown connection type.")
        except socket.error as e:
            raise IOError(f"Error sending command '{command}': {e}") from e

    def open_shutter(self) -> None:
        '''Open the Bonn Shutter.'''
        if self.state['is_connected'] is False:
            raise RuntimeError("Shutter is not connected")
        try:
            state = self._parse_ss(self.send_command(self.Cmds.OPEN))
            if state != 1:
                raise RuntimeError("Shutter failed to open")
            self.state['is_open'] = True
            self.state['last_command'] = self.Cmds.OPEN
            self.state['shutter_state'] = state
        except Exception as e:
            self.state['error_code'] = str(e)
            raise RuntimeError(f"Failed to open shutter: {e}") from e

    def close_shutter(self) -> None:
        '''Close the Bonn Shutter.'''
        if self.state['is_connected'] is False:
            raise RuntimeError("Shutter is not connected")
        try:
            state = self._parse_ss(self.send_command(self.Cmds.CLOSE))
            if state == 1:
                raise RuntimeError("Shutter failed to close")
            self.state['is_open'] = False
            self.state['last_command'] = self.Cmds.CLOSE
            self.state['shutter_state'] = state
        except Exception as e:
            self.state['error_code'] = str(e)
            raise RuntimeError(f"Failed to close shutter: {e}") from e

    def get_status(self) -> dict:
        '''Get the status of the Bonn Shutter.'''
        self.status["A"] = self._parse_sv(self.send_command(self.Cmds.CHECK_STATUS + " 1"))
        self.status["B"] = self._parse_sv(self.send_command(self.Cmds.CHECK_STATUS + " 2"))
        self.status["system"] = self.send_command(self.Cmds.CHECK_STATUS + " 0")
        return self.status

###############################################################################
# Private helper methods for parsing responses

    def _read_until_prompt_usb(self, timeout=1.0) -> list[str]:
        '''
        Read lines until 'c>' prompt is seen.
        Returns a list of decoded response lines (excluding prompt).
        '''
        lines = []
        self.dev.timeout = timeout
        while True:
            raw = self.dev.readline()
            if not raw:
                break
            line = raw.decode("utf-8", errors="ignore").strip()
            if line == "c>":
                break
            if line:
                lines.append(line)
        return lines

    def _read_until_prompt_socket(self, timeout=1.0) -> list[str]:
        '''socket version of read until prompt'''
        self.socket.settimeout(timeout)
        buffer = ""
        lines = []
        while True:
            chunk = self.socket.recv(1024).decode("utf-8", errors="ignore")
            if not chunk:
                break
            buffer += chunk
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if line == "c>":
                    return lines
                if line:
                    lines.append(line)
        return lines

    def _parse_sv(self, lines: list[str]) -> dict:
        '''Parse 'sv x' response into structured flags'''
        status = {
            "blade": None,
            "flags": {}
        }

        for line in lines:
            if line.startswith("Blade"):
                status["blade"] = line.split()[-1]
                continue

            if "ON" in line:
                key = line.replace("ON", "").strip()
                status["flags"][key] = True
            else:
                status["flags"][line.strip()] = False

        return status

    def _parse_ss(self, lines: list[str]) -> int | None:
        '''parse 'ss' response to get shutter state'''
        if not lines:
            return None

        try:
            return int(lines[0].split()[0])
        except ValueError:
            return None

    def close_loop(self) -> bool:
        '''Close the loop for the hardware motion device.'''
        raise NotImplementedError("This device does not support this type of control")

    def is_loop_closed(self) -> bool:
        '''Check if the hardware motion loop is closed.'''
        raise NotImplementedError("This device does not support this type of control")

    def home(self) -> bool:
        '''Home the hardware motion device.'''
        raise NotImplementedError("This device does not support this type of control")

    def is_homed(self) -> bool:
        '''Check if the hardware motion device is homed.'''
        raise NotImplementedError("This device does not support this type of control")

    def get_pos(self, *args, **kwargs) -> Union[float, int, None]:
        '''Get the position of the hardware motion device.'''
        raise NotImplementedError("This device does not support this type of control")

    def set_pos(self, *args, **kwargs) -> bool:
        '''Set the position of the hardware motion device.'''
        raise NotImplementedError("This device does not support this type of control")

    def get_limits(self) -> Union[Dict[str, Tuple[float, float]], None]:
        '''
        Get the limits of the hardware motion device.

        Limits are the smallest and largest allowed positions for an axis.
        Axes are identified by a string and limits are a tuple.
        e.g.: {"1": (1, 6)} - for a filter wheel

        '''
        raise NotImplementedError("This device does not support this type of control")
