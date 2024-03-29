Утилита финальной подготовки наборов команд для лазерной/плоттерной резки.

Функционал.

1. Конвертирование выходного HPGL HP(v) ArtiosCAD в модифицированный HPGL для лазерных комплексов. Генерация g-code для комплекса FATA.
2. Разделение композитного выходного чертежа основания штанцформы на гравировку, паз и обрезку.
3. Отделение диагональных фрагментов паза.
4. Разделение паза различной толщины.
5. Комбинация линейного и контурного паза в единый четреж для однопроходной резки.

Во входном .PLT все дуги должны быть аппроксимированы линиями. Из примитивов учитываются только линии. Команды, описывающие иные объекты, будут проигнорированы или могут вызвать ошибку выполнения.

Начальные настройки.

Структура файла конфигурации config.ini (должен находиться в директории запуска утилиты):

(Секция путей. Директории указаны для примера.)
[Paths]
input_dir = z:\pltout\line         (расположение линейного исходного PLT)
slot_input_dir = z:\pltout\slot    (расположение контурного исходного PLT)
plt_out_dir = z:\pltout\done       (расположение готовых PLT)
iso_out_dir = z:\pltout\done       (расположение готовых ISO)

(Секция диагоналей)
[Diagonals]
min_diag = 22.5                     (минимальный угол диагонали)
max_diag = 67.5                     (максимальный угол диагонали)

(Секция масштаба)
[PLTUnits]
scale_factor = 3937                 (Условных единиц в мм)

(Секция параметров и вставок g-code)
[ISOParameters]
file_prefix = g72                   (Начало набора команд)
move_prefix =                       (Команды перед началом движения)
plot_prefix = o1                    (Команды перед началом резки)
	G4P0.6
plot_postfix = o2                   (Команды после окончания резки)
file_postfix = o16                  (Завершающий набор команд. Многострочные записываются
	g4p3                             с новой строки с отступом)
	g1x0y0f4
	o0
etch_speed = 1.5                    (Скорость гравировки)
rules_speed = 0.3                   (Скорость резки паза)
wood_speed = 0.5                    (Скорость обрезки)
run_speed = 3.0                     (Скорость холостого перемещения)

Запуск, ключи.

Консольная утилита запускается в формате "pazotron.[py|pyw|exe] [-s +c +d +iso]".
Важно не допускать одновременного запуска двух и более экземпляров утилиты: из-за конфликтов результаты работы будут непредсказуемыми.

Запуск без ключей - режим разделения линейного чертежа без учета диагоналей. Утилита ищет во входной директории файлы .PLT и последовательно их обрабатывает, после успешной записи результата в выходную директорию исходные файлы удаляются.
В процессе работы происходит отделение пазов разной толщины (2, 3, 4, 6 pt) и запись их в отдельные файлы. Имена задаются согласно исходному с удалением первых трёх символов и добавлением в конец имени "n" для гравировки, "p" для паза, "o" для обрезки. В случае наличия паза различной толщины, добавляется ещё одня "p": "0000p.plt", "0000pp.plt" и т. д.

-s - режим "без разделения". Только конвертирование HPGL(v) -> PLT. Имя не меняется, разделения не происходит. Подходит для экспорта резки образцов и т. п.

+d - отделение диагоналей. Аналогичен режиму без ключей, но диагонали с заданными углами отделяются в файлы с окончанием "d": "0000pd.plt", "0000ppd.plt" и т. д. Ключ может работать в сочетании с +iso.

+c - комбинация линейного и контурного паза. Поиск линейных PLT, поисх совпадающих по имени с добавлением "_slot" в директории для контурных. При успехе поиска оба исходника объединяются и записывается выходной PLT. Исходные файлы удаляются. Для паза записывается два выходных файла: "0000p.plt" - линейный, "0000c.plt" - комбинированный.
Толщина паза и диагонали игнорируются.

+iso - генерация g-code. Аналогичен режиму без ключей, но на выходе два файла: .PLT и .ISO. Записываюся в указанные в конфигурации или в параметрах запуска директории. Ключ может работать в сочетании с +d.

+plt_out=z:\pltout\done - принудительное указание расположения готовых PLT.

+iso_out=z:\pltout\done - принудительное указание расположения готовых ISO.

Разделение.
Разделение гравировки, обрезки и паза по толщинам происходит по параметру "номер инструмента" в исходном PLT. Для этого нужно привести в соответствие параметры экспорта из САПР:
1:  паз 2pt,
3:  паз 3pt,
5:  паз 4pt,
10: паз 6pt,
8:  основание (обрезка),
9:  отверстия в основании,
7:  гравировка
