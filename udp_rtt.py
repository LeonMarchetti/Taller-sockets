import getopt
import socket
import sys
import time

# Parametros por defecto para host y puerto:
HOST       = 'localhost'
PORT       = 65000
TAM_BUFFER = 1024

def server():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((HOST, PORT))
        print('Escuchando en: <{}:{}>'.format(HOST, PORT))
        while True:
            datos, cliente = s.recvfrom(TAM_BUFFER)
            if datos:
                mensaje = ''
                s.sendto(mensaje.encode(), cliente)

def client(t, n):
    lista_rtt = []
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        for i in range(0, n):
            inicio = time.time()

            s.sendto('rtt'.encode(), (HOST, PORT))
            datos, _ = s.recvfrom(TAM_BUFFER)

            fin = time.time()
            rtt = fin - inicio
            lista_rtt.append(rtt)

            print('Rtt({}): {}'.format(i, rtt))

            time.sleep(t)

    if len(lista_rtt) > 0:
        print('Promedio de RTT: {}'.format(sum(lista_rtt)/len(lista_rtt)))
        print('RTT mayor:       {}'.format(max(lista_rtt)))
        print('RTT menor:       {}'.format(min(lista_rtt)))

if __name__ == '__main__':

    # Parametros de la linea de comandos:
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'csi:p:t:n:')
    except getopt.GetoptError:
        print('Error con los parametros: ' + str(sys.argv))
        sys.exit(1)

    # Valores por defecto para host y puerto:
    t = None # Cada cuanto se sondea al servidor.
    n = None # Cantidad de veces que se va a tomar el tiempo.

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
        elif opt == '-t': # Tiempo entre sondeos
            t = int(arg)
        elif opt == '-n': # Cantidad de sondeos
            n = int(arg)

    if modo == '':
        print('Usar "-c" para modo Cliente y "-s" para modo Servidor')
    elif modo == 's':
        server()
    elif modo == 'c':
        if t is None or n is None:
            print('Ingresar tiempo entre sondeos y cantidad de sondeos!')
        else:
            client(t, n)
