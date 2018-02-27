import datetime
import getopt
import socket
import sys

""" PDU:
Pedido:
 0
 0             7
+-+-+-+-+-+-+-+-+
|     Huso      |
+-+-+-+-+-+-+-+-+
Huso: 8 bits
  El huso horario

Respuesta:
Segun RFC 867:
    dd mmm yy hh:mm:ss uuuuuuuuu

Daytime string: 28 bytes
  Fecha y tiempo actual con el huso horario especificado.
"""

# Parámetros por defecto para host y puerto:
HOST       = 'localhost'
PORT       = 65000
TAM_MSG    = 28
TAM_BUFFER = 1024

MESES = ('ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN',
         'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DEC')

FORMATO_RESPUESTA = '{0:0>2} {1:>3} {2:0>2} {3:0>2}:{4:0>2}:{5:0>2} {6}'

def armar_respuesta(ahora, huso):
    # ahora => datetime.datetime.now(tzs) : datetime.datetime
    # huso => tz.tzname(ahora) : str
    return FORMATO_RESPUESTA.format(
        ahora.day,
        MESES[ahora.month-1],
        ahora.year % 100,
        ahora.hour,
        ahora.minute,
        ahora.second,
        huso
    )

def server():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((HOST, PORT))
        print('Escuchando en: <{}:{}>'.format(HOST, PORT))
        while True:
            datos, cliente = s.recvfrom(TAM_BUFFER)
            if datos:
                # Proceso del pedido:
                huso = int.from_bytes(datos, 'big') - 24
                td = datetime.timedelta(hours=huso)
                tz = datetime.timezone(td)
                ahora = datetime.datetime.now(tz)
                mensaje = armar_respuesta(ahora, tz.tzname(ahora))

                # Responder:
                print('Enviado > ' + mensaje)
                s.sendto(mensaje.encode(), cliente)

def client(huso):
    if huso == '':
        huso = int(input('Ingrese huso horario (entre -23 y 23)> '))

    if huso <= -24 or huso >= 24:
        print('El huso horario tiene que estar entre -23 y 23.')
        return

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        # Pedido
        h = huso + 24 # No se pueden transmitir enteros negativos
        s.sendto(h.to_bytes(1, 'big'), (HOST, PORT))

        # Respuesta:
        datos, _ = s.recvfrom(TAM_BUFFER)
        resp = datos.decode()
        if len(resp) == TAM_MSG:
            print(datos.decode())
        else:
            print('Error con el mensaje')

if __name__ == '__main__':

    # Parametros de la linea de comandos:
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'csi:p:h:')
    except getopt.GetoptError:
        print('Error con los parametros: ' + str(sys.argv))
        sys.exit(1)

    modo = '' # modo Cliente o Servidor
    huso = None

    for opt, arg in opts:
        if opt == '-c': # Modo Cliente
            if modo == '':
                modo = 'c'
            else:
                print('Error... no se puede ser cliente y servidor al mismo tiempo!')
                sys.exit(1)
        elif opt == '-s': # Modo Servidor
            if modo == '':
                modo = 's'
            else:
                print('Error... no se puede ser cliente y servidor al mismo tiempo!')
                sys.exit(1)
        elif opt == '-i': # Direccion IP
            HOST = arg
        elif opt == '-p': # Puerto
            PORT = int(arg)
        elif opt == '-h':
            huso = int(arg)

    if modo == '':
        print('Usar "-c" para modo Cliente y "-s" para modo Servidor')
    elif modo == 'c':
        if huso is None:
            print('No se ingreso el huso horario')
        else:
            client(huso)
    elif modo == 's':
        server()
