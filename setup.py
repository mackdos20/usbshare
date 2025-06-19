from setuptools import setup, find_packages

setup(
    name="usb-redi",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'websockets==11.0.3',
        'PyQt5==5.15.9',
        'cryptography==41.0.7',
        'watchdog==3.0.0',
        'psutil==5.9.8',
        'pywin32==306',
        'qrcode==7.4.2',
        'Pillow==10.0.0',
        'pycryptodome==3.19.0',
        'python-dotenv==1.0.0',
        'aiohttp==3.9.1',
        'asyncio==3.4.3',
        'pyserial==3.5',
        'zeroconf==0.131.0',
        'stun==0.1.0',
        'pyusb==1.2.1'
    ],
    python_requires='>=3.8',
) 