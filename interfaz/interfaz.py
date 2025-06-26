import tkinter as tk
from tkinter import messagebox
from threading import Thread
import os
import simpleaudio as sa
from clonador import (
    grabarAudio, detenerYGuardarGrabacion, cargarAudio,
    transcribirYDetectar, traducirTexto, clonarVoz,
    sintetizarVozBark, diccionarioIdiomasXTTS, diccionarioIdiomasNLLB
)

# Función principal para iniciar la interfaz gráfica
def iniciarInterfaz():
    ventana = tk.Tk()
    ventana.title("Traductor Multilenguaje - Voz Inteligente")
    ventana.geometry("580x600")

    # Variables de estado
    idiomaObjetivo = tk.StringVar(value="english")
    entradaRuta = tk.StringVar()
    textoDetectado = tk.StringVar()
    textoTraducidoVar = tk.StringVar()
    idiomaDetectadoVar = tk.StringVar()
    modoSeleccionado = tk.StringVar(value="clonar")
    generoSeleccionado = tk.StringVar(value="neutral")
    emocionSeleccionada = tk.StringVar(value="neutral")

    # Reproduce un archivo de audio en un hilo
    def reproducirAudio(ruta):
        def reproducir():
            try:
                wave_obj = sa.WaveObject.from_wave_file(ruta)
                play_obj = wave_obj.play()
                play_obj.wait_done()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo reproducir: {e}")
        Thread(target=reproducir).start()

    # Acción de grabar audio
    def accionGrabar():
        def grabar():
            botonGrabar.config(state="disabled")
            etiquetaEstadoProceso.config(text="Iniciando grabación...", fg="green")
            botonDetener.pack(side=tk.LEFT, padx=5)
            grabarAudio()
        Thread(target=grabar).start()

    # Acción de detener grabación y guardar
    def accionDetener():
        def detener():
            etiquetaEstadoProceso.config(text="Deteniendo y guardando...", fg="green")
            ruta = detenerYGuardarGrabacion()
            if ruta:
                entradaRuta.set(ruta)
                etiquetaEstadoProceso.config(text="Audio grabado correctamente", fg="green")
                procesarAudio(ruta)
                botonReproducir.pack(side=tk.LEFT, padx=5)
            else:
                etiquetaEstadoProceso.config(text="No se pudo guardar el audio", fg="red")
            botonGrabar.config(state="normal")
            botonDetener.pack_forget()
        Thread(target=detener).start()

    # Acción de cargar audio desde archivo
    def accionCargar():
        ruta = cargarAudio()
        if ruta == "LARGO":
            messagebox.showwarning("Advertencia", "El audio excede los 10 segundos.")
            etiquetaEstadoProceso.config(text="Audio demasiado largo", fg="red")
        elif ruta:
            entradaRuta.set(ruta)
            etiquetaEstadoProceso.config(text="Audio cargado correctamente", fg="green")
            procesarAudio(ruta)
            botonReproducir.pack(side=tk.LEFT, padx=5)

    # Procesamiento del audio para transcripción e idioma
    def procesarAudio(ruta):
        try:
            if not ruta or not os.path.exists(ruta):
                etiquetaEstadoProceso.config(text="Archivo no encontrado o inválido", fg="red")
                return
            if os.path.getsize(ruta) < 2048:
                etiquetaEstadoProceso.config(text="El archivo de audio parece estar vacío", fg="red")
                return

            etiquetaEstadoProceso.config(text="Transcribiendo audio...", fg="green")
            texto, idioma = transcribirYDetectar(ruta)
            textoDetectado.set(texto)
            idiomaDetectadoVar.set(idioma)
            etiquetaTextoTranscrito.config(text=f"Texto detectado: {texto}")
            etiquetaIdiomaDetectado.config(text=f"Idioma detectado: {idioma}")
            etiquetaTraduccion.config(text="")
            etiquetaEstadoProceso.config(text="Transcripción completada", fg="green")
        except Exception as e:
            print("Error en procesarAudio:", e)
            etiquetaEstadoProceso.config(text="No se pudo procesar el audio", fg="red")

    # Traduce el texto detectado
    def traducirTextoDetectado():
        try:
            texto = textoDetectado.get()
            

            if not texto.strip():
                etiquetaTraduccion.config(text="No hay texto para traducir", fg="red")
                return

            idiomaOrigen = idiomaDetectadoVar.get()
            idiomaClave = idiomaObjetivo.get()

            if idiomaClave not in diccionarioIdiomasNLLB:
                etiquetaTraduccion.config(text="Idioma objetivo no válido", fg="red")
                return

            idiomaDestino = diccionarioIdiomasNLLB[idiomaObjetivo.get()]


            etiquetaTraduccion.config(text="Traduciendo...", fg="blue")
            ventana.update_idletasks()

            traduccion = traducirTexto(texto, idiomaOrigen, idiomaDestino)
            textoTraducidoVar.set(traduccion)
            etiquetaTraduccion.config(text=f"Traducción: {traduccion}", fg="black")
        except Exception as e:
            etiquetaTraduccion.config(text="Error al traducir", fg="red")
            print("Error en traducción:", e)
    # Acción de clonar voz (con autorización explícita de xtts config)
    def accionClonar():
        def ejecutar():
            try:
                etiquetaEstadoProceso.config(text="Clonando voz...", fg="green")

                textoOriginal = textoDetectado.get()
                idiomaClave = idiomaObjetivo.get()

                idiomaOrigen = idiomaDetectadoVar.get()
                idiomaDestino = diccionarioIdiomasXTTS[idiomaClave]
                idiomaDestinoNLLB = diccionarioIdiomasNLLB[idiomaClave]

                # Limitar longitud por seguridad
                if len(textoOriginal) > 250:
                    textoOriginal = textoOriginal[:250]

                # Traducir al idioma destino
                textoTraducido = traducirTexto(textoOriginal, idiomaOrigen, idiomaDestinoNLLB)
                textoTraducidoVar.set(textoTraducido)

                # Limpieza de archivo anterior si existe
                if os.path.exists("voz_clonada.wav"):
                    os.remove("voz_clonada.wav")

                # Llamar a clonador con el texto traducido
                clonarVoz(textoTraducido, entradaRuta.get(), idiomaDestino)

                etiquetaEstadoProceso.config(text="voz_clonada.wav generada", fg="green")
                botonReproducirGenerado.config(command=lambda: reproducirAudio("voz_clonada.wav"))
                botonReproducirGenerado.pack(pady=2)
            except Exception as e:
                etiquetaEstadoProceso.config(text="Error al clonar voz", fg="red")
                print("Error al clonar voz:", e)
        Thread(target=ejecutar).start()
        # Acción de sintetizar voz
    def accionSintetizar():
        def ejecutar():
            try:
                etiquetaEstadoProceso.config(text="Sintetizando voz...", fg="green")
                texto = textoTraducidoVar.get()
                if not texto:
                    texto = textoDetectado.get()
                idiomaClave = idiomaObjetivo.get()
                genero = generoSeleccionado.get()
                sintetizarVozBark(texto, idiomaClave, genero)
                etiquetaEstadoProceso.config(text="voz_sintetica.wav generada", fg="green")
                botonReproducirGenerado.config(command=lambda: reproducirAudio("voz_sintetica.wav"))
                botonReproducirGenerado.pack(pady=2)
            except Exception as e:
                etiquetaEstadoProceso.config(text="Error al sintetizar voz", fg="red")
                print("Error al sintetizar voz:", e)
        Thread(target=ejecutar).start()

    # Muestra opciones de síntesis solo si se selecciona Bark, y oculta el botón de clonar
    def mostrarOpcionesSintesis(mostrar):
        if mostrar:
            frameSintesis.pack()
            botonClonar.pack_forget()
        else:
            frameSintesis.pack_forget()
            botonClonar.pack(pady=5)

    # Elementos de la interfaz
    tk.Label(ventana, text="Ruta del audio:").pack()
    tk.Entry(ventana, textvariable=entradaRuta, width=60).pack()

    etiquetaEstadoProceso = tk.Label(ventana, text="", fg="green")
    etiquetaEstadoProceso.pack()

    frameGrabacion = tk.Frame(ventana)
    frameGrabacion.pack(pady=5)

    botonGrabar = tk.Button(frameGrabacion, text="Grabar audio", command=accionGrabar)
    botonGrabar.pack(side=tk.LEFT, padx=5)

    botonCargar = tk.Button(frameGrabacion, text="Cargar audio", command=accionCargar)
    botonCargar.pack(side=tk.LEFT, padx=5)

    botonReproducir = tk.Button(frameGrabacion, text="Reproducir audio", command=lambda: reproducirAudio(entradaRuta.get()))
    botonDetener = tk.Button(frameGrabacion, text="Detener grabación", command=accionDetener)

    frameIdioma = tk.Frame(ventana)
    frameIdioma.pack(pady=5)
    tk.Label(frameIdioma, text="Idioma objetivo:").pack(side=tk.LEFT)
    tk.OptionMenu(frameIdioma, idiomaObjetivo, *diccionarioIdiomasXTTS.keys()).pack(side=tk.LEFT)
    tk.Button(frameIdioma, text="Traducir texto", command=traducirTextoDetectado).pack(side=tk.LEFT)

    tk.Label(ventana, text="¿Qué deseas hacer?").pack()
    tk.Radiobutton(ventana, text="Clonar voz", variable=modoSeleccionado, value="clonar", command=lambda: mostrarOpcionesSintesis(False)).pack()
    tk.Radiobutton(ventana, text="Sintetizar con Bark", variable=modoSeleccionado, value="sintetizar", command=lambda: mostrarOpcionesSintesis(True)).pack()

    # Opciones específicas de Bark (género/emoción)
    frameSintesis = tk.Frame(ventana)
    tk.Label(frameSintesis, text="Género:").pack()
    tk.OptionMenu(frameSintesis, generoSeleccionado, "male", "female", "neutral").pack()
    tk.Button(frameSintesis, text="Sintetizar voz", command=accionSintetizar).pack()
    frameSintesis.pack_forget()

    # Botón clonar (solo visible cuando se selecciona esa opción)
    botonClonar = tk.Button(ventana, text="Clonar voz", command=accionClonar)
    botonClonar.pack(pady=5)

    # Etiquetas de resultado
    etiquetaTextoTranscrito = tk.Label(ventana, text="", wraplength=500)
    etiquetaTextoTranscrito.pack()
    etiquetaIdiomaDetectado = tk.Label(ventana, text="")
    etiquetaIdiomaDetectado.pack()
    etiquetaTraduccion = tk.Label(ventana, text="", wraplength=500)
    etiquetaTraduccion.pack()

    # Botón para reproducir voz generada
    botonReproducirGenerado = tk.Button(ventana, text="Reproducir voz generada")

    ventana.mainloop()

if __name__ == "__main__":
    iniciarInterfaz()
