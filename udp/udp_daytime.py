# coding=utf-8
"""
Parámetros:
* -c    Modo cliente
* -s    Modo servidor
* -i    Dirección IP o nombre de host
* -p    Número de puerto
* -h    Huso horario como diferencia de tiempo del UTC

PDU:
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


import datetime
import getopt
import socket
import sys


TAM_MSG = 28
MESES = ('ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN',
         'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DEC')
FORMATO_TIEMPO = '%d %b %y %H:%M:%S %z'


def server(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as servidor:
        servidor.bind((host, port))
        print('Escuchando en: <{}:{}>'.format(host, port))
        while True:
            datos, cliente = servidor.recvfrom(1)
            if datos:
                # Proceso del pedido:
                huso = int.from_bytes(datos, 'big', signed=True)
                print('Recibido de <{}:{}> > huso={}'.format(cliente[0], cliente[1], huso))

                # Armo la respuesta:
                mensaje = armar_respuesta(huso)

                # Respondo:
                print('Enviado > ' + mensaje)
                servidor.sendto(mensaje.encode(), cliente)


def armar_respuesta(huso):
    td = datetime.timedelta(hours=huso)
    tz = datetime.timezone(td)
    ahora = datetime.datetime.now(tz)
    return ahora.strftime(FORMATO_TIEMPO)


def client(host, port, huso):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as cliente:
        # Pedido:
        datos_salida = huso.to_bytes(1, 'big', signed=True)
        cliente.sendto(datos_salida, (host, port))

        # Respuesta:
        datos_entrada, _ = cliente.recvfrom(TAM_MSG)
        respuesta = datos_entrada.decode()

        # Muestro resultado:
        if validar(respuesta):
            print(respuesta)
        else:
            print('Error con el mensaje: <{}>'.format(respuesta))


def validar(mensaje):
    try:
        datetime.datetime.strptime(mensaje, FORMATO_TIEMPO)
    except ValueError:
        return False

    return True


def main(argv):
    try:
        opts, _ = getopt.getopt(argv[1:], 'csi:p:h:')
    except getopt.GetoptError:
        print('Error con los parámetros: {}'.format(str(argv)))
        sys.exit(1)

    # Valores por defecto para host y puerto:
    host = 'localhost'
    port = 1313

    modo = ''  # modo Cliente o Servidor
    huso = None

    for opt, arg in opts:
        if opt == '-c':  # Modo Cliente
            if modo == '':
                modo = 'c'
            else:
                print('Error... no se puede ser cliente y servidor al mismo tiempo!')
                sys.exit(1)
        elif opt == '-s':  # Modo Servidor
            if modo == '':
                modo = 's'
            else:
                print('Error... no se puede ser cliente y servidor al mismo tiempo!')
                sys.exit(1)
        elif opt == '-i':  # Direccion IP
            host = arg
        elif opt == '-p':  # Puerto
            port = int(arg)
        elif opt == '-h':
            try:
                huso = int(arg)
                if not -23 <= huso <= 23:
                    raise ValueError
            except ValueError:
                print('-h: Huso tiene que ser un número entre -23 y 23')
                sys.exit(1)

    if modo == '':
        print('Usar "-c" para modo Cliente y "-s" para modo Servidor')
    elif modo == 'c':
        if huso is None:
            print('No se ingresó el huso horario')
        else:
            client(host, port, huso)
    elif modo == 's':
        server(host, port)


if __name__ == '__main__':
    main(sys.argv)
