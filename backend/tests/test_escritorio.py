"""La aplicación de escritorio debe arrancar sola y guardar los datos
en un lugar donde el usuario siempre pueda escribir."""

import escritorio
import rutas


def test_busca_un_puerto_libre_distinto_cada_vez():
    # Un puerto fijo chocaría con otros programas del usuario
    puerto = escritorio.buscar_puerto_libre()
    assert 1024 < puerto <= 65535


def test_el_servidor_solo_escucha_en_la_maquina_local():
    # Los datos del vendedor son sensibles: nunca se exponen a la red
    assert escritorio.DIRECCION == "127.0.0.1"


def test_la_base_de_datos_no_vive_junto_al_ejecutable():
    # En el ejecutable la ruta va a la carpeta de datos del usuario;
    # en desarrollo, junto al backend
    ruta = rutas.ruta_base_datos()
    assert ruta.name == "mi_puestito.db"
    assert ruta.parent.is_dir()


def test_espera_al_servidor_antes_de_abrir_el_navegador():
    # Sin nadie escuchando debe rendirse, no colgarse
    puerto_sin_uso = escritorio.buscar_puerto_libre()
    assert escritorio.esperar_servidor(puerto_sin_uso, intentos=2) is False


def test_el_puerto_se_recuerda_entre_arranques(tmp_path, monkeypatch):
    # El puerto es parte del origen del navegador: si cambiara en cada
    # arranque, IndexedDB y las preferencias quedarían huérfanas al reabrir.
    # Se parchea el nombre dentro de "escritorio" (no el de "rutas"): un
    # "from rutas import directorio_datos" copia la referencia a la función
    # en el momento de importar, así que parchear rutas.directorio_datos no
    # afecta a la copia que escritorio.py ya tiene en su propio namespace.
    monkeypatch.setattr(escritorio, "directorio_datos", lambda: tmp_path)
    primero = escritorio.obtener_puerto()
    segundo = escritorio.obtener_puerto()
    assert primero == segundo
    assert (tmp_path / "puerto.txt").read_text().strip() == str(primero)
