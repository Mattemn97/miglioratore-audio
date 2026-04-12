#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modulo Enterprise per l'Ottimizzazione Massiva di File Audio
Esegue routine di normalizzazione, riduzione del rumore, equalizzazione e compressione
dinamica su interi dataset tramite elaborazione batch asincrona.
"""

import sys
from pathlib import Path
from typing import List

import numpy as np
import noisereduce as nr
from pydub import AudioSegment, effects
from scipy.signal import butter, lfilter

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)

# Importazione del logger aziendale
from custom_logger import logger


# ==========================================
# CORE: Filtri di Elaborazione del Segnale
# ==========================================

def apply_highpass_filter(data: np.ndarray, sample_rate: int, cutoff: int = 80) -> np.ndarray:
    """
    Applica un filtro passa-alto per rimuovere frequenze sub-basse e rimbombi.
    """
    b, a = butter(2, cutoff / (0.5 * sample_rate), btype='high', analog=False)
    return lfilter(b, a, data)


def reduce_boxiness(data: np.ndarray, sample_rate: int, freq_low: int = 200, freq_high: int = 400, gain_db: int = -3) -> np.ndarray:
    """
    Attenua la banda medio-bassa per ridurre l'effetto 'scatola' della registrazione.
    """
    b, a = butter(
        2,
        [freq_low / (0.5 * sample_rate), freq_high / (0.5 * sample_rate)],
        btype='band'
    )
    filtered = lfilter(b, a, data)
    factor = 10 ** (gain_db / 20)
    return data + (filtered * factor)


def boost_presence_band(data: np.ndarray, sample_rate: int, freq_low: int = 3000, freq_high: int = 5000, gain_db: int = 3) -> np.ndarray:
    """
    Esaltazione della banda di presenza (3kHz - 5kHz) per migliorare l'intelligibilità vocale.
    """
    b, a = butter(
        2,
        [freq_low / (0.5 * sample_rate), freq_high / (0.5 * sample_rate)],
        btype='band'
    )
    boosted = lfilter(b, a, data)
    factor = 10 ** (gain_db / 20)
    return data + (boosted * factor)


# ==========================================
# CORE: Pipeline di Ottimizzazione
# ==========================================

def process_audio_file(
    input_path: Path, 
    output_path: Path,
    do_noise: bool, 
    do_eq: bool, 
    do_deesser: bool, 
    do_comp: bool, 
    do_sat: bool, 
    do_limit: bool
) -> bool:
    """
    Applica la catena di elaborazione audio parametrizzata su un singolo file.
    
    :param input_path: Percorso del file sorgente.
    :param output_path: Percorso del file di destinazione.
    :param do_*: Flag booleani per l'attivazione dei singoli moduli di elaborazione.
    :return: True in caso di elaborazione riuscita, False altrimenti.
    """
    try:
        audio = AudioSegment.from_file(str(input_path))
        sample_rate = audio.frame_rate
        samples = np.array(audio.get_array_of_samples()).astype(np.float32)

        # 1. Noise Reduction
        if do_noise:
            samples = nr.reduce_noise(y=samples, sr=sample_rate)

        # 2. Equalizzazione Strutturale (High-pass + Boxiness + Presence)
        if do_eq:
            samples = apply_highpass_filter(samples, sample_rate)
            samples = reduce_boxiness(samples, sample_rate)
            samples = boost_presence_band(samples, sample_rate)

        # 3. De-Esser Dedicato (Attenuazione 5-8 kHz)
        if do_deesser:
            b, a = butter(2, [5000 / (sample_rate * 0.5), 8000 / (sample_rate * 0.5)], btype='band')
            sibilance = lfilter(b, a, samples)
            samples -= sibilance * 0.4

        # 4. Compressione Dinamica
        if do_comp:
            audio_temp = AudioSegment(
                samples.astype(np.int16).tobytes(),
                frame_rate=sample_rate,
                sample_width=audio.sample_width,
                channels=audio.channels
            )
            audio_temp = effects.compress_dynamic_range(audio_temp)
            samples = np.array(audio_temp.get_array_of_samples()).astype(np.float32)

        # 5. Saturazione Armonica Leggera
        if do_sat:
            samples = samples * 1.02
            samples = np.tanh(samples) * 32767

        # 6. Limiter
        if do_limit:
            peak = np.max(np.abs(samples))
            if peak > 0:
                samples = samples * (30000 / peak)

        # Ricostruzione ed esportazione
        out_audio = AudioSegment(
            samples.astype(np.int16).tobytes(),
            frame_rate=sample_rate,
            sample_width=audio.sample_width,
            channels=audio.channels
        )
        
        out_audio.export(str(output_path), format="wav")
        logger.debug(f"Traccia elaborata e salvata con successo: {output_path.name}")
        return True

    except Exception as e:
        logger.error(f"Fallimento critico durante l'elaborazione del file {input_path.name}: {e}", exc_info=True)
        return False


def discover_audio_files(directory: Path) -> List[Path]:
    """Scansiona la directory alla ricerca di estensioni audio supportate."""
    supported_extensions = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
    return [p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in supported_extensions]


# ==========================================
# INTERFACCIA: Logica UI e Terminale
# ==========================================

def main() -> None:
    """Metodo di orchestrazione principale dell'interfaccia a riga di comando."""
    console = Console()
    console.clear()

    # Banner Aziendale
    console.print("[bold cyan]=============================================================[/bold cyan]")
    console.print("[bold white]            SISTEMA DI AUTO-MIGLIORAMENTO AUDIO PRO          [/bold white]")
    console.print("[bold cyan]=============================================================[/bold cyan]\n")
    logger.info("Avvio del modulo di elaborazione batch audio.")

    # 1. Configurazione Percorsi
    while True:
        src_input = Prompt.ask("Inserire il percorso della directory SORGENTE").strip().strip('"')
        src_dir = Path(src_input)
        if src_dir.is_dir():
            break
        logger.warning(f"L'operatore ha inserito un percorso sorgente non valido: {src_input}")
        console.print("[bold red]Errore: Directory sorgente inesistente. Riprovare.[/bold red]")

    dst_input = Prompt.ask("Inserire il percorso della directory di DESTINAZIONE").strip().strip('"')
    dst_dir = Path(dst_input)
    
    try:
        dst_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Directory di destinazione configurata: {dst_dir.resolve()}")
    except Exception as e:
        logger.critical(f"Impossibile creare la directory di destinazione: {e}")
        console.print("[bold red]Errore critico: Impossibile creare o accedere alla directory di destinazione. Uscita.[/bold red]")
        return

    # 2. Rilevamento Asset
    audio_files = discover_audio_files(src_dir)
    if not audio_files:
        logger.warning(f"Nessun file audio compatibile rilevato in {src_dir.resolve()}")
        console.print("[bold yellow]Attenzione: Nessun asset sonoro individuato nella cartella indicata. Operazione annullata.[/bold yellow]")
        return

    # 3. Configurazione Moduli DSP
    console.print("\n[bold]Parametri di Elaborazione e Filtraggio DSP[/bold]")
    
    do_noise = Confirm.ask("Attivare Noise Reduction algoritmica?", default=True)
    do_eq = Confirm.ask("Attivare Equalizzazione Strutturale (HPF, Boxiness, Presence)?", default=True)
    do_deesser = Confirm.ask("Attivare De-Esser (5-8 kHz)?", default=True)
    do_comp = Confirm.ask("Attivare Compressione Dinamica?", default=True)
    do_sat = Confirm.ask("Attivare Saturazione Armonica leggera?", default=False)
    do_limit = Confirm.ask("Attivare Limiter Finale (-0.5 dBFS approx)?", default=True)

    # 4. Tabella Riepilogo
    summary_table = Table(title="Riepilogo Configurazione Pipeline", header_style="bold magenta")
    summary_table.add_column("Parametro Strategico", style="dim")
    summary_table.add_column("Stato")

    summary_table.add_row("Directory Sorgente", str(src_dir.resolve()))
    summary_table.add_row("Directory Destinazione", str(dst_dir.resolve()))
    summary_table.add_row("Volume Tracce Rilevate", str(len(audio_files)))
    summary_table.add_row("Modulo Noise Reduction", "Attivo" if do_noise else "Inattivo")
    summary_table.add_row("Modulo Equalizzazione", "Attivo" if do_eq else "Inattivo")
    summary_table.add_row("Modulo De-Esser", "Attivo" if do_deesser else "Inattivo")
    summary_table.add_row("Modulo Compressione", "Attivo" if do_comp else "Inattivo")
    summary_table.add_row("Modulo Saturazione", "Attivo" if do_sat else "Inattivo")
    summary_table.add_row("Modulo Limiter", "Attivo" if do_limit else "Inattivo")

    console.print("\n")
    console.print(summary_table)
    console.print("\n")

    if not Confirm.ask("Confermare l'avvio della procedura batch sui file audio?"):
        logger.info("L'utente ha annullato l'operazione in fase di conferma.")
        console.print("Elaborazione annullata dal sistema.")
        return

    # 5. Elaborazione Batch con Progress Bar
    logger.info("Inizio routine di elaborazione massiva audio.")
    successful_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        
        task_id = progress.add_task("[cyan]Applicazione DSP in corso...", total=len(audio_files))

        for file_path in audio_files:
            output_filename = f"{file_path.stem}_edit.wav"
            output_path = dst_dir / output_filename

            success = process_audio_file(
                input_path=file_path,
                output_path=output_path,
                do_noise=do_noise,
                do_eq=do_eq,
                do_deesser=do_deesser,
                do_comp=do_comp,
                do_sat=do_sat,
                do_limit=do_limit
            )

            if success:
                successful_count += 1
            
            progress.advance(task_id)

    # 6. Report Finale
    logger.info(f"Routine completata. File processati con successo: {successful_count}/{len(audio_files)}.")
    
    console.print("\n[bold green]--- ELABORAZIONE COMPLETATA ---[/bold green]")
    console.print(f"Tracce processate correttamente: [bold cyan]{successful_count}[/bold cyan] su [bold cyan]{len(audio_files)}[/bold cyan].")
    console.print(f"I file audio (formato WAV) sono stati archiviati in: {dst_dir.resolve()}")
    console.print("\nChiusura del modulo terminata senza anomalie operative.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Interruzione forzata dall'operatore (KeyboardInterrupt).")
        Console().print("\n[bold yellow]Sospensione operativa richiesta dall'utente. Terminazione istantanea.[/bold yellow]")
        sys.exit(0)
    except Exception as unexpected_e:
        logger.critical(f"Fallimento irreversibile a livello di sistema: {unexpected_e}", exc_info=True)
        Console().print("\n[bold red]Arresto critico del programma. Consultare la diagnostica nei log di sistema.[/bold red]")
        sys.exit(1)