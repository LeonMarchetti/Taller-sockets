import getopt
import socket
import sys
import zlib

HOST       = 'localhost'
PORT       = 65000
TAM_BUFFER = 1024
SEPARADOR  = b'|' # Separa el checksum y el mensaje en una transmision.

def armar_mensaje(mensaje):
    # Comprimir mensaje:
    mensaje_comp = zlib.compress(mensaje.encode())

    # Calcular checksum del mensaje comprimido, y convertirlo en bytes:
    cs_crc = zlib.crc32(mensaje_comp)

    # Informacion de la transimision:
    print('Mensaje enviado:')
    print('Tamano descomprimido: {}'.format(len(mensaje.encode())))
    print('Tamano comprimido:    {}'.format(len(mensaje_comp)))
    print('Checksum:             {}'.format(cs_crc))

    # Unir ambos en un string de bytes, usando un separador para separar ambos valores:
    return cs_crc.to_bytes(4, 'big') + SEPARADOR + mensaje_comp

def mostrar_mensaje(datos):
    # Separo checksum y mensaje:
    checksum, mensaje_comp = datos.split(SEPARADOR)

    checksum_int = int.from_bytes(checksum, 'big')

    # Comparar checksum:
    if zlib.crc32(mensaje_comp) != checksum_int :
        print('Hubo un error en la transmision!')
    else:
        mensaje = zlib.decompress(mensaje_comp)
        print('< ' + mensaje.decode())

        # Informacion de la transmision:
        print('Mensaje recibido:')
        print('Tamano descomprimido: {}'.format(len(mensaje)))
        print('Tamano comprimido:    {}'.format(len(mensaje_comp)))
        print('Checksum:             {}'.format(checksum_int))

def server():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((HOST, PORT))
        print('Escuchando en: <{}:{}>'.format(HOST, PORT))
        while True:
            # Recibir mensaje del cliente:
            datos_in, cliente = s.recvfrom(TAM_BUFFER)
            mostrar_mensaje(datos_in)

            # Enviar mensaje al cliente:
            mensaje = input('> ')
            datos_out = armar_mensaje(mensaje)
            s.sendto(datos_out, cliente)

def client():
    servidor = (HOST, PORT)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        while True:
            # Enviar mensaje a cliente:
            mensaje = input('> ')
            datos_out = armar_mensaje(mensaje)
            s.sendto(datos_out, servidor)

            # Recibir mensaje del servidor:
            datos_in, _ = s.recvfrom(TAM_BUFFER)
            mostrar_mensaje(datos_in)

if __name__ == '__main__':
    # Parametros de la linea de comandos:
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'csi:p:')
    except getopt.GetoptError:
        print('Error con los parametros: ' + str(sys.argv))
        sys.exit(1)

    modo = ''

    for opt, arg in opts:
        if opt == '-c': # Modo Cliente
            if modo == '':
                modo = 'c'
            else:
                print('Error... no se puede ser cliente y servidor al mismo tiempo!')
        elif opt == '-s': # Modo Servidor
            if modo == '':
                modo = 's'
            else:
                print('Error... no se puede ser cliente y servidor al mismo tiempo!')
        elif opt == '-i': # Direccion IP
            HOST = arg
        elif opt == '-p': # Puerto
            PORT = int(arg)

    if modo == '':
        print('Usar "-c" para modo Cliente y "-s" para modo Servidor')
    elif modo == 's':
        server()
    elif modo == 'c':
        client()