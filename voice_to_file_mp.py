import multiprocessing
import threading
import time
import soundcard as sc
import soundfile as sf
from datetime import datetime
import logging
import os
import numpy as np
from connect import connect_to_postgres


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
        self.create_table()
        self.stop_event = multiprocessing.Event()
        self.processes = []

    def create_table(self):
        #connection = sqlite3.connect("voise_data.db")
        connection = connect_to_postgres()
        cursor = connection.cursor()
        #cursor.execute("CREATE TABLE IF NOT EXISTS files_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, start_time text)")
        cursor.execute("CREATE TABLE IF NOT EXISTS files_queue (id SERIAL PRIMARY KEY, name TEXT, start_time text)")
        cursor.execute("CREATE TABLE IF NOT EXISTS time_record (time_record TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS voise_settings (id SERIAL PRIMARY KEY, param_name TEXT NOT NULL, param_value TEXT NOT NULL);")
        cursor.execute("DELETE FROM files_queue")
        cursor.execute("DELETE FROM time_record")
        #cursor.execute("DELETE FROM voise_settings")
        connection.commit()
        cursor.close()


    # def load_settings(self):
    #     file_path = r'c:\Users\user\PycharmProjects\lifeTRanslater\voise_settings.yml'
    #     try:
    #         with open(file_path, 'r') as file:
    #             settings = yaml.safe_load(file)
    #             self.run = settings.get("run")
    #             self.duration = settings.get("duration_spinBox")
    #             self.path = settings.get("pathlabel")
    #     except FileNotFoundError:
    #         print(f"File not found: {file_path}")
    #     except yaml.YAMLError as e:
    #         print(f"Error loading YAML file: {e}")

    def load_settings(self):
        self.run = bool(self.load_settings_from_db("run"))
        self.duration = int(self.load_settings_from_db("duration_spinBox"))
        self.path = self.load_settings_from_db("pathlabel")

    def load_settings_from_db(self,param_name):

        # SQL query to load settings
        query_select = f"""
        SELECT param_value 
        FROM voise_settings
        where param_name= %s;
        """

        try:
            conn = connect_to_postgres()
            cursor = conn.cursor()
            cursor.execute(query_select,(param_name,))
            results = cursor.fetchone()

            # Creating a dictionary from the results
            param_value = results[0]

            # Updating the UI components with the loaded settings
            if param_value:
                return param_value
            else:
                print(f'Нет {param_name} данных о параметре')
                return None
        except Exception as e:
            print(f'Ошибка при загрузке настроек {param_name}: {e}')
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()

    def disable(self):
        self.run = False
    def listen_comp_work(self, vRECORD_SECONDS, v_file_name):
        try:
            SAMPLE_RATE = 44100  # [Hz]. sampling rate.
            with sc.get_microphone(id=str(sc.default_speaker().name), include_loopback=True).recorder(
                    samplerate=SAMPLE_RATE) as mic:
                # record audio with loopback from default speaker.
                data = mic.record(numframes=SAMPLE_RATE * vRECORD_SECONDS)
                bempty = np.all(data == 0)
                bsilent = self.is_silent(data)
                if not bempty and not bsilent:
                    sf.write(file=v_file_name, data=data[:, 0], samplerate=SAMPLE_RATE)
                    # self.appQueue.enqueue(v_file_name)
                    print(f"Записали файл {v_file_name}")
                    return True
                else:
                    return False
        except Exception as ee:
            print(f'Ошибка при записи файла {v_file_name}, длительность {vRECORD_SECONDS}')
            print(ee)
            raise


    def is_silent(self, data):
        SILENCE_THRESHOLD = 0.001  # Threshold for considering the audio as silent
        # Calculate the RMS value of the audio data
        rms_value = np.sqrt(np.mean(data ** 2))
        return rms_value < SILENCE_THRESHOLD

    def listen_mic_work(self, vRECORD_SECONDS, v_file_name):
        try:
            SAMPLE_RATE = 44100
            mic = sc.default_microphone()
            with mic.recorder(samplerate=SAMPLE_RATE) as recorder:
                # record audio with loopback from default speaker.
                data = recorder.record(numframes=SAMPLE_RATE* vRECORD_SECONDS)
                bempty = np.all(data == 0)
                bsilent = self.is_silent(data)
                if not bempty and not bsilent:
                    sf.write(file=v_file_name, data=data[:, 0], samplerate=SAMPLE_RATE)
                    # self.appQueue.enqueue(v_file_name)
                    print(f"Записали файл {v_file_name}")
                    return True
                else:
                    return False
        except Exception as ee:
            print(f'Ошибка при записи файла {v_file_name}, длительность {vRECORD_SECONDS}')
            print(ee)
            raise


    def del_off(self):
        #connection = sqlite3.connect("voise_data.db")
        connection = connect_to_postgres()
        cursor = connection.cursor()
        cursor.execute("select id, name FROM files_queue")
        data = cursor.fetchall()
        for rec in data:
            if os.path.exists(rec[1]):
                os.remove(rec[1])
        cursor.execute(f"delete FROM files_queue")
        connection.commit()
        cursor.close()

    def unique_sequential_generator(self,start=0):
        num = start
        while True:
            yield num
            num += 1

    def write_to_file(self, stop_event, proc, sign):
        total_time = 0
        #connection = sqlite3.connect("voise_data.db")
        connection = connect_to_postgres()
        cursor = connection.cursor()
        gen = self.unique_sequential_generator()
        while not stop_event.is_set():
            self.load_settings()
            if not self.run:
                print('Запись остановлена')
                break
            start_time = time.time()
            self.count+=1
            current_datetime = datetime.now()
            date_string = current_datetime.strftime("%Y%m%d%H%M%S")
            time_string = current_datetime.strftime("%H:%M:%S")
            seq = next(gen)
            filename = f'{self.path}/{sign}{str(seq)}{date_string}_{self.count}.wav'
            #self.listen_comp_work(self.duration,filename)
            res = proc(self.duration, filename)
            # Sleep for some time before the next write
            #threading.Event().wait(1)
            elapsed_time = time.time() - start_time
            total_time+=elapsed_time
            #self.time_label.setText('Время записи '+str(round(total_time)))
            if res:
                cursor.execute(f"insert into files_queue(name, start_time) values ('{filename}', '{time_string}')")
                cursor.execute(f"delete from time_record")
                cursor.execute(f"INSERT INTO time_record VALUES ('{str(round(total_time))}')")
                connection.commit()
                logging.debug(f'{filename} {str(round(total_time))}')
        cursor.close()
        self.del_off()
        connection.close()

    def start_processes(self):
        if not self.processes or all(not p.is_alive() for p in self.processes):
            self.stop_event.clear()

            p1 = multiprocessing.Process(target=self.write_to_file, args=(self.stop_event, self.listen_mic_work, 'mc'))
            p2 = multiprocessing.Process(target=self.write_to_file, args=(self.stop_event, self.listen_comp_work, 'cp'))

            p1.start()
            p2.start()

            self.processes = [p1, p2]


    def stop_processes(self):
        self.stop_event.set()
        for p in self.processes:
            if p.is_alive():
                p.join()



    # def run_tread(self):
    #     write_thread = threading.Thread(target=self.write_to_file, args=(self.listen_mic_work,'mc'))
    #     write_thread1 = threading.Thread(target=self.write_to_file, args=(self.listen_comp_work,'cp'))
    #     logging.debug(f'Запускаю поток')
    #     write_thread.start()
    #     write_thread1.start()
    #     write_thread.join()
    #     write_thread1.join()

def listen_init():
    configure_logging()
    lListen = Listen()
    return lListen

# if __name__ == '__main__':
#      configure_logging()
#      lListen = Listen()
#      #lListen.write_to_file(lListen.listen_mic_work,'mc')
#      lListen.run_tread()