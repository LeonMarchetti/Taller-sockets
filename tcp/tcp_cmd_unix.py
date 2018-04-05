# coding=utf-8
import getopt
import socket
import subprocess
import sys


class ArgExcepcion(Exception):
    pass


class ConexionTerminadaExcepcion(Exception):
    pass


BUFFER = 1024
SEPARADOR = b'\\'


def enviar(s, mensaje):
    datos = mensaje + SEPARADOR
    while datos:
        enviado = s.send(datos)
        if enviado == 0:
            raise ConexionTerminadaExcepcion()
        datos = datos[enviado:]


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

    return b''.join([cacho for cacho in cachos])


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


def server(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((host, port))
        servidor.listen(5)
        print('Escuchando en <{}:{}>'.format(host, port))

        try:
            while True:
                print('Esperando conexión...')
                cliente, direccion = servidor.accept()
                print('Conexión establecida: <{}:{}>'.format(direccion[0],
                                                             direccion[1]))
                try:
                    while True:
                        # Recibir comando:
                        comando = recibir(cliente).decode()
                        print('Recibido: <{}>'.format(comando))
                        resultado = ejecutar_comando(comando)

                        # Enviar resultado:
                        enviar(cliente, resultado.encode())

                except ConexionTerminadaExcepcion:
                    print('Conexión terminada')
                finally:
                    cliente.close()
        except KeyboardInterrupt:
            print('Programa terminado')


def client(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.connect((host, port))
        try:
            while True:
                comando = ingresar_comando()
                if comando:
                    enviar(servidor, comando.encode())
                else:
                    break

                print(recibir(servidor).decode())

        except ConexionTerminadaExcepcion:
            pass


def main():
    try:
        # Parámetros de la línea de comandos:
        opts, _ = getopt.getopt(sys.argv[1:], 'csi:p:')

        modo = ''
        
        # Valores por defecto para host y puerto:
        host = 'localhost'
        port = 65000

        for opt, arg in opts:
            if opt == '-c':  # Modo Cliente
                if modo == '':
                    modo = 'c'
                else:
                    raise ArgExcepcion('Error... no se puede ser cliente y '
                                       'servidor al mismo tiempo!')
            elif opt == '-s':  # Modo Servidor
                if modo == '':
                    modo = 's'
                else:
                    raise ArgExcepcion('Error... no se puede ser cliente y '
                                       'servidor al mismo tiempo!')
            elif opt == '-i':  # Dirección IP
                host = arg
            elif opt == '-p':  # Puerto
                port = int(arg)

        if modo == '':
            print('Usar "-c" para modo Cliente y "-s" para modo Servidor')
        elif modo == 's':
            server(host, port)
        elif modo == 'c':
            client(host, port)

    except getopt.GetoptError:
        print('Error con los parámetros: ' + str(sys.argv))
    except ArgExcepcion as e:
        print('{}'.format(e))


if __name__ == '__main__':
    main()
