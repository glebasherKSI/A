import mysql.connector
import sys
import traceback

def test_mysql_connection(host="localhost", user="root", password="", database="Centamash"):
    """Функция для тестирования подключения к MySQL"""
    print("Python версия:", sys.version)
    print("MySQL Connector версия:", mysql.connector.__version__)
    print("\n=== Тестирование соединения с MySQL ===")
    
    # Вывод параметров подключения
    print("Параметры подключения:")
    print(f"- Хост: {host}")
    print(f"- Пользователь: {user}")
    print(f"- База данных: {database}")
    
    try:
        # Шаг 1: Подключение к MySQL серверу без указания базы данных
        print("\nШаг 1: Подключение к MySQL серверу без указания базы данных...")
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            connect_timeout=60,
            read_timeout=60
        )
        print("✅ Успешное подключение к MySQL серверу!")
        
        print("\nПроверка активных соединений...")
        cursor = connection.cursor()
        cursor.execute("SHOW PROCESSLIST")
        processes = cursor.fetchall()
        
        active_processes = [p for p in processes if p[4] != 'Sleep']
        print(f"Всего соединений: {len(processes)}")
        print(f"Активных соединений: {len(active_processes)}")
        
        if active_processes:
            print("\nДетали активных соединений:")
            for process in active_processes:
                print(f"- ID: {process[0]}, User: {process[1]}, Host: {process[2]}, DB: {process[3]}, Command: {process[4]}, Time: {process[5]}, State: {process[6]}")
        
        # Получаем ID текущего соединения
        cursor.execute("SELECT CONNECTION_ID()")
        current_connection_id = cursor.fetchone()[0]
        print(f"\nID текущего соединения: {current_connection_id}")
        
        print("\nЗакрытие лишних соединений...")
        killed = 0
        for process in processes:
            process_id = process[0]
            process_user = process[1]
            
            # Пропускаем текущее соединение
            if process_id == current_connection_id:
                continue
                
            # Закрываем все соединения этого же пользователя
            if process_user == user:
                try:
                    cursor.execute(f"KILL {process_id}")
                    killed += 1
                    print(f"Закрыто соединение {process_id} пользователя {process_user}")
                except Exception as e:
                    print(f"Ошибка при закрытии соединения {process_id}: {e}")
            
            # Также закрываем все соединения в ожидании блокировки
            elif process[6] and "Waiting for table metadata lock" in process[6]:
                try:
                    cursor.execute(f"KILL {process_id}")
                    killed += 1
                    print(f"Закрыто зависшее соединение {process_id}")
                except Exception as e:
                    print(f"Ошибка при закрытии соединения {process_id}: {e}")
        
        print(f"\nВсего закрыто соединений: {killed}")
        
        # Проверяем повторно, сколько соединений осталось
        cursor.execute("SHOW PROCESSLIST")
        remaining_processes = cursor.fetchall()
        print(f"Осталось соединений: {len(remaining_processes)}")
        
        # Проверяем права пользователя
        print("\nПроверка прав пользователя...")
        cursor.execute("SHOW GRANTS")
        grants = cursor.fetchall()
        print("Права пользователя:")
        for grant in grants:
            print(f"- {grant[0]}")
            
        # Проверяем доступные базы данных
        print("\nДоступные базы данных:")
        cursor.execute("SHOW DATABASES")
        dbs = cursor.fetchall()
        db_names = [db[0] for db in dbs]
        for db in db_names:
            print(f"- {db}")
            
        # Проверяем, существует ли указанная база данных
        if database.lower() in [db.lower() for db in db_names]:
            print(f"\n✅ База данных '{database}' существует!")
        else:
            print(f"\n❌ База данных '{database}' не найдена!")
            print("Попытка создания базы данных...")
            try:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                print(f"✅ База данных '{database}' успешно создана!")
            except mysql.connector.Error as create_error:
                print(f"❌ Ошибка при создании базы данных: {create_error}")
                print(f"   MySQL Error Code: {create_error.errno}")
                print(f"   MySQL Error Message: {create_error.msg}")
                if create_error.errno == 1044:  # Ошибка доступа
                    print("\n⚠️ У пользователя нет прав на создание базы данных!")
                    print("Рекомендация: Используйте пользователя с правами администратора или выполните следующую команду в MySQL:")
                    print(f"GRANT ALL PRIVILEGES ON {database}.* TO '{user}'@'%';")
                    print("FLUSH PRIVILEGES;")
                
        cursor.close()
        connection.close()
        
        # Шаг 2: Попытка подключения к указанной базе данных
        print("\nШаг 2: Подключение к базе данных...")
        try:
            conn = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database,
                connect_timeout=10
            )
            print(f"✅ Успешное подключение к базе данных '{database}'!")
            
            # Проверяем существующие таблицы
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            if tables:
                print("\nСуществующие таблицы:")
                for table in tables:
                    print(f"- {table[0]}")
            else:
                print("\nВ базе данных нет таблиц.")
                
            # Пробуем создать тестовую таблицу
            print("\nПопытка создания тестовой таблицы...")
            try:
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS `test_table` (
                    `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    `name` VARCHAR(50) NOT NULL,
                    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """)
                print("✅ Тестовая таблица создана успешно!")
                
                # Пробуем вставить тестовые данные
                print("\nПопытка вставки тестовых данных...")
                cursor.execute("INSERT INTO `test_table` (`name`) VALUES ('test_value')")
                conn.commit()
                print("✅ Тестовые данные успешно добавлены!")
                
                # Пробуем прочитать данные
                print("\nПопытка чтения данных...")
                cursor.execute("SELECT * FROM `test_table` LIMIT 1")
                row = cursor.fetchone()
                if row:
                    print(f"✅ Данные успешно прочитаны: id={row[0]}, name={row[1]}")
                else:
                    print("❌ Данные не найдены!")
                    
            except mysql.connector.Error as table_error:
                print(f"❌ Ошибка при работе с таблицей: {table_error}")
                print(f"   MySQL Error Code: {table_error.errno}")
                print(f"   MySQL Error Message: {table_error.msg}")
            
            cursor.close()
            conn.close()
            
        except mysql.connector.Error as db_error:
            print(f"❌ Ошибка при подключении к базе данных: {db_error}")
            print(f"   MySQL Error Code: {db_error.errno}")
            print(f"   MySQL Error Message: {db_error.msg}")
            
            if db_error.errno == 1049:  # База данных не существует
                print("\n⚠️ База данных не существует!")
                print("Рекомендация: Убедитесь, что база данных создана или у пользователя есть права на её создание.")
    
    except mysql.connector.Error as error:
        print(f"❌ Ошибка при подключении к MySQL серверу: {error}")
        print(f"   MySQL Error Code: {error.errno}")
        print(f"   MySQL Error Message: {error.msg}")
        
        if error.errno == 2003:  # Can't connect to MySQL server
            print("\n⚠️ Не удалось подключиться к MySQL серверу!")
            print("Рекомендации:")
            print("1. Убедитесь, что сервер MySQL запущен")
            print("2. Проверьте правильность указанного хоста и порта")
            print("3. Убедитесь, что брандмауэр не блокирует соединение")
            
        elif error.errno == 1045:  # Access denied for user
            print("\n⚠️ Отказано в доступе для пользователя!")
            print("Рекомендации:")
            print("1. Проверьте правильность имени пользователя и пароля")
            print("2. Убедитесь, что пользователь имеет права доступа с указанного хоста")
    
    print("\n=== Тестирование завершено ===")

if __name__ == "__main__":
    # Получаем параметры подключения из командной строки
    args = sys.argv[1:]
    host = args[0] if len(args) > 0 else "91.209.226.31"
    user = args[1] if len(args) > 1 else "USER"
    password = args[2] if len(args) > 2 else "password"
    database = args[3] if len(args) > 3 else "Centramash"
    
    try:
        test_mysql_connection(host, user, password, database)
    except Exception as e:
        print(f"❌ Необработанная ошибка: {e}")
        print(traceback.format_exc()) 