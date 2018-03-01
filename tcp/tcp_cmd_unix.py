# coding=utf-8
import getopt
import socket
import subprocess
import sys


class ArgExcepcion(Exception):
    pass


class ConexionTerminadaExcepcion(Exception):
    pass


# Valores por defecto para host y puerto:
HOST = 'localhost'
PORT = 65000
BUFFER = 1024
SEPARADOR = b'\\'


def ejecutar_comando(comando):
    lista_comando = comando.split(' ')
    try:
        cp = subprocess.run(lista_comando,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True)

        resultado = cp.stdout
        if cp.stderr:
            resultado += b'\r\n' + cp.stderr
        return resultado

    except subprocess.CalledProcessError as error:
        print('Error: \n{}'.format(error.output))


def ingresar_comando():
    return input('>>> ')


def enviar(s, mensaje):
    try:
        b_mensaje = mensaje.encode() + SEPARADOR
    except AttributeError:
        b_mensaje = mensaje + SEPARADOR

    while b_mensaje:
        enviado = s.send(b_mensaje)
        if enviado == 0:
            raise ConexionTerminadaExcepcion()
        b_mensaje = b_mensaje[enviado:]


def recibir(s):
    cachos = []
    while True:
        cacho = s.recv(BUFFER)
        if cacho == b'':
            raise ConexionTerminadaExcepcion()

        # Busco el separador en el cacho:
        f = cacho.find(SEPARADOR)
        if f > -1:
            cachos.append(cacho[:f])
            break
        else:
            cachos.append(cacho)

    return ''.join([cacho.decode() for cacho in cachos])


def server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((HOST, PORT))
        servidor.listen(5)
        print('Escuchando en <{}:{}>'.format(HOST, PORT))

        try:
            while True:
                print('Esperando conexión...')
                cliente, direccion = servidor.accept()
                print('Conexión establecida: <{}:{}>'.format(direccion[0], direccion[1]))
                try:
                    while True:
                        # Recibir comando:
                        comando = recibir(cliente)
                        print('Recibido: <{}>'.format(comando))
                        resultado = ejecutar_comando(comando)

                        # Enviar resultado:
                        enviar(cliente, resultado)

                except ConexionTerminadaExcepcion:
                    print('Conexión terminada')
                finally:
                    cliente.close()
        except KeyboardInterrupt:
            print('Programa terminado')


def client():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.connect((HOST, PORT))
        try:
            while True:
                comando = ingresar_comando()
                if comando:
                    enviar(servidor, comando)
                else:
                    break

                print(recibir(servidor))

        except ConexionTerminadaExcepcion:
            pass


if __name__ == '__main__':
    try:
        # Parámetros de la línea de comandos:
        opts, _ = getopt.getopt(sys.argv[1:], 'csi:p:')

        modo = ''

        for opt, arg in opts:
            if opt == '-c':  # Modo Cliente
                if modo == '':
                    modo = 'c'
                else:
                    raise ArgExcepcion('Error... no se puede ser cliente y servidor al mismo tiempo!')
            elif opt == '-s':  # Modo Servidor
                if modo == '':
                    modo = 's'
                else:
                    raise ArgExcepcion('Error... no se puede ser cliente y servidor al mismo tiempo!')
            elif opt == '-i':  # Dirección IP
                HOST = arg
            elif opt == '-p':  # Puerto
                PORT = int(arg)

        if modo == '':
            print('Usar "-c" para modo Cliente y "-s" para modo Servidor')
        elif modo == 's':
            server()
        elif modo == 'c':
            client()

    except getopt.GetoptError:
        print('Error con los parámetros: ' + str(sys.argv))
    except ArgExcepcion as e:
        print('{}'.format(e))
