# -*- coding: utf-8 -*-
import errno
import os
import signal
import socket


# noinspection PyUnresolvedReferences,PyUnusedLocal
def guarderia(signum, frame):
    """When a child process exits, the kernel sends a SIGCHLD signal. The
    parent process can set up a signal handler to be asynchronously notified of
    that SIGCHLD event and then it can wait for the child to collect its
    termination status, thus preventing the zombie process from being left
    around.
    """
    while True:
        try:
            pid, estado = os.waitpid(-1, os.WNOHANG)

        except OSError:
            return

        if pid == 0:
            return


class ServidorFork:
    """
    Clase servidor que atiende a consultas de múltiples cliente, usando el
    método os.fork.
    """
    def __init__(self, direccion, proceso):
        """
        Inicia el servidor.
        :param direccion: Par dirección IP y número de puerto que usará el \
        servidor.
        :param proceso: Función que acepta un objeto socket y devuelva los \
        datos a enviar por tal socket.
        """
        socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,
                                       1)
            socket_servidor.bind(direccion)
            socket_servidor.listen(5)
            print('Escuchando en <{}:{}>'.format(direccion[0], direccion[1]))

            signal.signal(signal.SIGCHLD, guarderia)

            while True:
                try:
                    socket_cliente, direccion_cliente = socket_servidor\
                                                            .accept()

                except IOError as e:
                    codigo, msg = e.args
                    if codigo == errno.EINTR:
                        continue

                    else:
                        print('Error: {}'.format(msg))
                        raise

                # Forkeo el proceso: El hijo  se encarga de atender al cliente
                pid = os.fork()
                if pid == 0:
                    socket_servidor.close()
                    self.proceso_hijo(socket_cliente, proceso)

                else:
                    socket_cliente.close()

                    print('Conexión establecida: ' +
                          '<{}:{}> con subproceso <{}>'.format(
                              direccion_cliente[0],
                              direccion_cliente[1],
                              pid))

        finally:
            socket_servidor.close()

    # noinspection PyProtectedMember
    @staticmethod
    def proceso_hijo(socket_cliente, proceso):
        try:
            # Recibe pedido y responde:
            socket_cliente.sendall(proceso(socket_cliente))

        finally:
            socket_cliente.close()
            os._exit(0)
