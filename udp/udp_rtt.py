# coding=utf-8
"""
Parámetros:
* -c    Modo cliente
* -s    Modo servidor
* -i    Dirección IP o nombre de host
* -p    Número de puerto
* -t    Tiempo entre sondeos en segundos
* -n    Cantidad de sondeos
"""
import getopt
import random
import socket
import string
import sys
import time

TAM_BUFFER = 1024


def server(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as servidor:
        servidor.bind((host, port))
        print('Escuchando en: <{}:{}>'.format(host, port))
        while True:
            datos, cliente = servidor.recvfrom(TAM_BUFFER)
            if datos:
                servidor.sendto(datos, cliente)
                print('Recibido: {}'.format(datos.decode()[:69]))


def client(host, port, t, n):
    lista_rtt = []
    cant_ok = 0
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as cliente:
        for i in range(1, n+1):
            # Mensaje aleatorio:
            mensaje = armar_mensaje()

            t_inicio = time.time()  # Tomo el tiempo antés de enviar el mensaje
            cliente.sendto(mensaje.encode(), (host, port))
            datos, _ = cliente.recvfrom(TAM_BUFFER)

            # Calculo el RTT:
            t_fin = time.time()
            rtt = t_fin - t_inicio
            lista_rtt.append(rtt)

            if datos.decode() == mensaje:
                msg_estado = 'OK'
                cant_ok += 1
            else:
                msg_estado = 'ERR'
            print('Rtt({0:3}): {1:10.5f} ms\t{2}'.format(i, rtt * 1000, msg_estado))

            # Tiempo de espera:
            time.sleep(t)

    # Resultados:
    if len(lista_rtt) > 0:
        # Se muestran los resultados en ms:
        avg = sum(lista_rtt) / len(lista_rtt) * 1000
        max_rtt = max(lista_rtt) * 1000
        min_rtt = min(lista_rtt) * 1000
        porc_ok = (cant_ok / len(lista_rtt)) * 100

        print(('===============================' +
               '\nPromedio de RTT: {0:10.5f} ms.' +
               '\nRTT mayor:       {1:10.5f} ms.' +
               '\nRTT menor:       {2:10.5f} ms.' +
               '\n% Éxito:         {3:10.5f}%.'
               ).format(avg, max_rtt, min_rtt, porc_ok))


def armar_mensaje():
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase +
                                                string.digits)
                   for _ in range(TAM_BUFFER))


def main(argv):
    # Parámetros de la línea de comandos:
    try:
        opts, _ = getopt.getopt(argv[1:], 'csi:p:t:n:')
    except getopt.GetoptError:
        print('Error con los parámetros: ' + str(argv))
        sys.exit(1)

    # Valores por defecto para host y puerto:
    host = 'localhost'
    port = 65000
    t = None  # Cada cuanto se sondea al servidor.
    n = None  # Cantidad de veces que se va a tomar el tiempo.

    modo = ''

    for opt, arg in opts:
        if opt == '-c':  # Modo Cliente
            if modo == '':
                modo = 'c'
            else:
                print('Error... no se puede ser cliente y servidor al mismo tiempo!')
        elif opt == '-s':  # Modo Servidor
            if modo == '':
                modo = 's'
            else:
                print('Error... no se puede ser cliente y servidor al mismo tiempo!')
        elif opt == '-i':  # Dirección IP
            host = arg
        elif opt == '-p':  # Puerto
            port = int(arg)
        elif opt == '-t':  # Tiempo entre sondeos
            t = float(arg)
        elif opt == '-n':  # Cantidad de sondeos
            n = int(arg)

    if modo == '':
        print('Usar "-c" para modo Cliente y "-s" para modo Servidor')
    elif modo == 's':
        server(host, port)
    elif modo == 'c':
        if t is None or n is None:
            print('¡Ingresar tiempo entre sondeos y cantidad de sondeos!')
        else:
            client(host, port, t, n)


if __name__ == '__main__':
    main(sys.argv)
