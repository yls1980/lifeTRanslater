import threading
import time
import soundcard as sc
import soundfile as sf
from datetime import datetime
import yaml
import sqlite3
import logging
import os


def configure_logging():
    # Configure the logging format
    logging.basicConfig(level=logging.DEBUG, filename='voise_app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s',datefmt='%Y-%m-%d %H:%M:%S' )

class Listen:
    run = False
    count = 0
    duration = 0
    path = ''
    def __init__(self):
        self.load_settings()
        self.connection = sqlite3.connect("voise_data.db")
        self.create_table()

    def create_table(self):
        self.cursor = self.connection.cursor()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS files_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, start_time text)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS time_record (time_record TEXT)")
        self.cursor.execute("DELETE FROM files_queue")
        self.cursor.execute("DELETE FROM time_record")
        self.cursor.close()


    def load_settings(self):
        file_path = r'c:\Users\user\PycharmProjects\lifeTRanslater\voise_settings.yml'
        try:
            with open(file_path, 'r') as file:
                settings = yaml.safe_load(file)
                self.run = settings.get("run")
                self.duration = settings.get("duration_spinBox")
                self.path = settings.get("pathlabel")
        except FileNotFoundError:
            print(f"File not found: {file_path}")
        except yaml.YAMLError as e:
            print(f"Error loading YAML file: {e}")

    def disable(self):
        self.run = False
    def listen_comp_work(self, vRECORD_SECONDS, v_file_name):
        try:
            SAMPLE_RATE = 48000  # [Hz]. sampling rate.
            with sc.get_microphone(id=str(sc.default_speaker().name), include_loopback=True).recorder(
                    samplerate=SAMPLE_RATE) as mic:
                # record audio with loopback from default speaker.
                data = mic.record(numframes=SAMPLE_RATE * vRECORD_SECONDS)
                sf.write(file=v_file_name, data=data[:, 0], samplerate=SAMPLE_RATE)
                # self.appQueue.enqueue(v_file_name)
                print(f"Записали файл {v_file_name}")
        except Exception as ee:
            print(f'Ошибка при записи файла {v_file_name}, длительность {vRECORD_SECONDS}')
            print(ee)
            raise

    def del_off(self):
        self.cursor = self.connection.cursor()
        self.cursor.execute("select id, name FROM files_queue")
        data = self.cursor.fetchall()
        for rec in data:
            if os.path.exists(rec[1]):
                os.remove(rec[1])
        self.cursor.execute(f"delete FROM files_queue")
        self.connection.commit()
        self.cursor.close()


    def write_to_file(self):
        total_time = 0
        self.cursor = self.connection.cursor()
        while True:
            self.load_settings()
            if not self.run:
                break
            start_time = time.time()
            self.count+=1
            current_datetime = datetime.now()
            date_string = current_datetime.strftime("%Y%m%d%H%M%S")
            time_string = current_datetime.strftime("%H:%M:%S")
            filename = f'{self.path}/v{date_string}_{self.count}.wav'
            self.listen_comp_work(self.duration,filename)
            # Sleep for some time before the next write
            #threading.Event().wait(1)
            elapsed_time = time.time() - start_time
            total_time+=elapsed_time
            #self.time_label.setText('Время записи '+str(round(total_time)))
            self.cursor.execute(f"insert into files_queue(name, start_time) values ('{filename}', '{time_string}')")
            self.cursor.execute(f"delete from time_record")
            self.cursor.execute(f"INSERT INTO time_record VALUES ('{str(round(total_time))}')")
            self.connection.commit()
            logging.debug(f'{filename} {str(round(total_time))}')
        self.cursor.close()
        self.del_off()
        self.connection.close()


    def run_tread(self):
        write_thread = threading.Thread(target=self.write_to_file())
        logging.debug(f'Запускаю поток')
        write_thread.start()
        write_thread.join()

if __name__ == '__main__':
    configure_logging()
    lListen = Listen()
    lListen.run_tread()