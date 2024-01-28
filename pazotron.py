from hpgl import parse_hpgl
import os, sys, math, configparser, time


def FError(filename):
    print('Невозможно открыть файл ' + filename)
    print('Нажмите ENTER...')
    input()
    sys.exit()


def PLTError(fname, err=''):
    print('Сбой расшифровки PLT-файла ' + fname + ':')
    print(err)
    print('Нажмите ENTER...')
    input()
    sys.exit()


def make_iso(collect: tuple, minX, minY, maxX, maxY, speed, marks):
    global gcode, string_num
    gcode = ''
    string_num = 0
    xGap = -minX
    yGap = -minY

    def normalize(coord, gap):
        return str(round((coord + gap) / scaleFactor, 3))

    def moveprefix():
        global string_num, gcode
        movePref = ISOMovePrefix.splitlines()
        for mp in movePref:
            string_num += 10
            gcode += str(string_num) + ' ' + mp + '\n'

    def goto(x, y, speed):
        global string_num, gcode
        string_num += 10
        gcode += str(string_num) + ' ' + 'G1' + 'X' + normalize(x, xGap) + 'Y' + normalize(y, yGap) + 'F' + speed + '\n'

    def drawprefix():
        global string_num, gcode
        drawPref = ISOPlotPrefix.splitlines()
        for dp in drawPref:
            string_num += 10
            gcode += str(string_num) + ' ' + dp + '\n'

    def drawpostfix():
        global string_num, gcode
        drawPost = ISOPlotPostfix.splitlines()
        for dp in drawPost:
            string_num += 10
            gcode += str(string_num) + ' ' + dp + '\n'

    if len(collect) > 0:
        filePref = ISOFilePrefix.splitlines()
        for fp in filePref:
            string_num += 10
            gcode += str(string_num) + ' ' + fp + '\n'
        if marks:
            moveprefix()
            goto(minX, minY, ISORunSpeed)
            drawprefix()
            goto(minX + scaleFactor, minY, speed)
            drawpostfix()
            moveprefix()
            goto(maxX, maxY, ISORunSpeed)
            drawprefix()
            goto(maxX - scaleFactor, maxY, speed)
            drawpostfix()
        moveprefix()
        goto(collect[0][0][0], collect[0][0][1], ISORunSpeed)
        drawprefix()
        goto(collect[0][1][0], collect[0][1][1], speed)
        lineCoordIter = iter(collect)
        for lineCoord in collect[1:]:
            lineCoordPrev = next(lineCoordIter)
            if (lineCoord[0][0] == lineCoordPrev[1][0]) and (lineCoord[0][1] == lineCoordPrev[1][1]):
                goto(lineCoord[1][0], lineCoord[1][1], speed)
            else:
                drawpostfix()
                moveprefix()
                goto(lineCoord[0][0], lineCoord[0][1], ISORunSpeed)
                drawprefix()
                goto(lineCoord[1][0], lineCoord[1][1], speed)
        drawpostfix()
        filePost = ISOFilePostfix.splitlines()
        for fp in filePost:
            string_num += 10
            gcode += str(string_num) + ' ' + fp + '\n'
    else:
        gcode = None

    return gcode


def PLTDraw(collect, marks, minX, minY, maxX, maxY):  # переписать по образу makeISO
    PLTOut = 'PU'
    if len(collect) > 0:
        if marks:
            PLTOut = ''
            PLTOut += 'PU%s %s\n' % (int(minX), int(minY))
            PLTOut += 'PD%s %s\n' % (int(minX + scaleFactor), int(minY))
            PLTOut += 'PU%s %s\n' % (int(maxX), int(maxY))
            PLTOut += 'PD%s %s\n' % (int(maxX - scaleFactor), int(maxY))
            PLTOut += 'PU'
        PLTOut = PLTOut + str(int(collect[0][0][0])) + ' ' + str(int(collect[0][0][1])) + '\n'
        PLTOut = PLTOut + 'PD' + str(int(collect[0][1][0])) + ' ' + str(int(collect[0][1][1])) + '\n'
        lineCoordIter = iter(collect)
        for lineCoord in collect[1:]:
            lineCoordPrev = next(lineCoordIter)
            if (lineCoord[0][0] == lineCoordPrev[1][0]) and (lineCoord[0][1] == lineCoordPrev[1][1]):
                PLTOut += 'PD' + str(int(lineCoord[1][0])) + ' ' + str(int(lineCoord[1][1])) + '\n'
            else:
                PLTOut += 'PU'
                PLTOut += str(int(lineCoord[0][0])) + ' ' + str(int(lineCoord[0][1])) + '\n'
                PLTOut += 'PD'
                PLTOut += str(int(lineCoord[1][0])) + ' ' + str(int(lineCoord[1][1])) + '\n'

    return PLTOut


def pasterise(PLTFile, marks=False, diagSearch='none'):
    # pen colors for separated PLT
    penCase = {
        1: 'rules',
        3: 'rules',
        5: 'rules',
        10: 'rules',
        8: 'wood',
        9: 'holes',
        7: 'etch'
    }
    rulesCase = {
        1: 'rules2pt',
        3: 'rules3pt',
        5: 'rules4pt',
        10: 'rules6pt',
    }

    # remove invalid PLT commands
    while True:
        try:
            with open(PLTFile, 'r+') as fl:
                gl = fl.read()
                break
        except IOError:
            print('Ожидание закрытия файла другим процессом...')
            time.sleep(1)
    print('Удаление паразитных команд из исходного файла...')
    gl = gl.replace('VS1,8;', '')
    gl = gl.replace('CT1;', '')
    gl = gl.replace('LT;', '')
    gl = gl.replace('PG;', '')
    gl = gl.replace('NR;', '')
    gl = gl.replace('SL;', '')

    with open(PLTFile, 'w') as fl:
        fl.write(gl)
        fl.flush()

    with open(PLTFile, 'r') as fl:
        print('Парсинг исходного файла...')
        try:
            ol, h1, h2 = parse_hpgl(fl)
        except Exception as err:
            PLTError(PLTFile, err)

    # main section
    PCollect2pt = []
    PCollect3pt = []
    PCOllect4pt = []
    PCollect6pt = []
    NCollect = []
    OCollect = []
    HCollect = []
    coordArray = []
    for line in ol:
        if line[0] in penCase:
            pen = penCase[line[0]]
        else:
            continue
        p, pw, lineCoord = line
        if separate:
            if pen == 'etch':
                NCollect.append(lineCoord)
            elif pen == 'rules':
                if combine:
                    if (diagSearch == 'diagonals') or (diagSearch == 'no_diagonals'):
                        try:
                            angleCoeff = (max((lineCoord[0][1], lineCoord[1][1])) - min(
                                (lineCoord[0][1], lineCoord[1][1]))) / \
                                         (max((lineCoord[0][0], lineCoord[1][0])) - min(
                                             (lineCoord[0][0], lineCoord[1][0])))
                        except:
                            angleCoeff = 0
                        angle = math.degrees(math.atan(angleCoeff))
                        if (angle > minDiag) and (angle < maxDiag) and (diagSearch == 'diagonals'):
                            PCollect2pt.append(lineCoord)
                        elif diagSearch == 'no_diagonals':
                            if (angle <= minDiag) or (angle >= maxDiag):
                                PCollect2pt.append(lineCoord)
                    elif diagSearch == 'none':
                        PCollect2pt.append(lineCoord)
                else:
                    if rulesCase[line[0]] == 'rules2pt':
                        if (diagSearch == 'diagonals') or (diagSearch == 'no_diagonals'):
                            try:
                                angleCoeff = (max((lineCoord[0][1], lineCoord[1][1])) - min(
                                    (lineCoord[0][1], lineCoord[1][1]))) / \
                                             (max((lineCoord[0][0], lineCoord[1][0])) - min(
                                                 (lineCoord[0][0], lineCoord[1][0])))
                            except:
                                angleCoeff = 0
                            angle = math.degrees(math.atan(angleCoeff))
                            if (angle > minDiag) and (angle < maxDiag) and (diagSearch == 'diagonals'):
                                PCollect2pt.append(lineCoord)
                            elif diagSearch == 'no_diagonals':
                                if (angle <= minDiag) or (angle >= maxDiag):
                                    PCollect2pt.append(lineCoord)
                        elif diagSearch == 'none':
                            PCollect2pt.append(lineCoord)
                    elif rulesCase[line[0]] == 'rules3pt':
                        if (diagSearch == 'diagonals') or (diagSearch == 'no_diagonals'):
                            try:
                                angleCoeff = (max((lineCoord[0][1], lineCoord[1][1])) - min(
                                    (lineCoord[0][1], lineCoord[1][1]))) / \
                                             (max((lineCoord[0][0], lineCoord[1][0])) - min(
                                                 (lineCoord[0][0], lineCoord[1][0])))
                            except:
                                angleCoeff = 0
                            angle = math.degrees(math.atan(angleCoeff))
                            if (angle > minDiag) and (angle < maxDiag) and (diagSearch == 'diagonals'):
                                PCollect3pt.append(lineCoord)
                            elif diagSearch == 'no_diagonals':
                                if (angle <= minDiag) or (angle >= maxDiag):
                                    PCollect3pt.append(lineCoord)
                        elif diagSearch == 'none':
                            PCollect3pt.append(lineCoord)
                    elif rulesCase[line[0]] == 'rules4pt':
                        if (diagSearch == 'diagonals') or (diagSearch == 'no_diagonals'):
                            try:
                                angleCoeff = (max((lineCoord[0][1], lineCoord[1][1])) - min(
                                    (lineCoord[0][1], lineCoord[1][1]))) / \
                                             (max((lineCoord[0][0], lineCoord[1][0])) - min(
                                                 (lineCoord[0][0], lineCoord[1][0])))
                            except:
                                angleCoeff = 0
                            angle = math.degrees(math.atan(angleCoeff))
                            if (angle > minDiag) and (angle < maxDiag) and (diagSearch == 'diagonals'):
                                PCOllect4pt.append(lineCoord)
                            elif diagSearch == 'no_diagonals':
                                if (angle <= minDiag) or (angle >= maxDiag):
                                    PCOllect4pt.append(lineCoord)
                        elif diagSearch == 'none':
                            PCOllect4pt.append(lineCoord)
                    elif rulesCase[line[0]] == 'rules6pt':
                        if (diagSearch == 'diagonals') or (diagSearch == 'no_diagonals'):
                            try:
                                angleCoeff = (max((lineCoord[0][1], lineCoord[1][1])) - min(
                                    (lineCoord[0][1], lineCoord[1][1]))) / \
                                             (max((lineCoord[0][0], lineCoord[1][0])) - min(
                                                 (lineCoord[0][0], lineCoord[1][0])))
                            except:
                                angleCoeff = 0
                            angle = math.degrees(math.atan(angleCoeff))
                            if (angle > minDiag) and (angle < maxDiag) and (diagSearch == 'diagonals'):
                                PCollect6pt.append(lineCoord)
                            elif diagSearch == 'no_diagonals':
                                if (angle <= minDiag) or (angle >= maxDiag):
                                    PCollect6pt.append(lineCoord)
                        elif diagSearch == 'none':
                            PCollect6pt.append(lineCoord)
            elif pen == 'wood':
                OCollect.append(lineCoord)
            elif pen == 'holes':
                HCollect.append(lineCoord)
        else:
            OCollect.append(lineCoord)
        coordArray.append(lineCoord)
    # holes to start of order
    for ll in OCollect:
        HCollect.append(ll)
    OCollect = HCollect

    xArray = list()
    yArray = list()

    for coord in coordArray:
        xArray.append(coord[0][0])
        xArray.append(coord[1][0])
        yArray.append(coord[0][1])
        yArray.append(coord[1][1])

    minX = min(xArray)
    minY = min(yArray)
    maxX = max(xArray)
    maxY = max(yArray)

    NOut = PLTDraw(NCollect, marks, minX, minY, maxX, maxY)
    POut2pt = PLTDraw(PCollect2pt, marks, minX, minY, maxX, maxY)
    POut3pt = PLTDraw(PCollect3pt, marks, minX, minY, maxX, maxY)
    POut4pt = PLTDraw(PCOllect4pt, marks, minX, minY, maxX, maxY)
    POut6pt = PLTDraw(PCollect6pt, marks, minX, minY, maxX, maxY)
    OOut = PLTDraw(OCollect, False, minX, minY, maxX, maxY)

    return NOut, POut2pt, POut3pt, POut4pt, POut6pt, OOut, \
        [NCollect, PCollect2pt, PCollect3pt, PCOllect4pt, PCollect6pt, OCollect], [minX, minY, maxX, maxY]


config = configparser.ConfigParser()
path = os.path.dirname(sys.argv[0])
try:
    config.read(os.path.join(path, 'config.ini'))

    # input dir
    srcdir = config['Paths']['input_dir']

    # slot input dir
    slot_srcdir = config['Paths']['slot_input_dir']

    # output dir
    donedir = config['Paths']['plt_out_dir']
    iso_donedir = config['Paths']['iso_out_dir']

    # diagonal angles
    minDiag = float(config['Diagonals']['min_diag'])
    maxDiag = float(config['Diagonals']['max_diag'])

    # PLT scale factor
    scaleFactor = int(config['PLTUnits']['scale_factor'])

    # ISO Parameters
    ISOFilePrefix: str = config['ISOParameters']['file_prefix']
    ISOMovePrefix: str = config['ISOParameters']['move_prefix']
    ISOPlotPrefix: str = config['ISOParameters']['plot_prefix']
    ISOPlotPostfix: str = config['ISOParameters']['plot_postfix']
    ISOFilePostfix: str = config['ISOParameters']['file_postfix']
    ISOEtchSpeed: str = config['ISOParameters']['etch_speed']
    ISORulesSpeed: str = config['ISOParameters']['rules_speed']
    ISOWoodSpeed: str = config['ISOParameters']['wood_speed']
    ISORunSpeed: str = config['ISOParameters']['run_speed']
except:
    print('Ошибка чтения конфигурации. Проверьте файл config.ini.')
    input('Нажмите ENTER...')

# command line parameters
separate = True
diagonals = False
combine = False
makeISO = False

if len(sys.argv) > 1:
    for param in sys.argv[1:]:
        if param == '-s': separate = False
        if param == '+d': diagonals = True
        if param == '+c': combine = True
        if param == '+iso': makeISO = True
        if param.startswith('+plt_out='): donedir = param[9:]
        if param.startswith('+iso_out='): iso_donedir = param[9:]

listOfFiles = os.listdir(srcdir)
if not listOfFiles:
    input('Не найдены файлы для обработки. Нажмите ENTER...')

for srcfile in listOfFiles:
    fullname = srcdir + '\\' + srcfile
    srcname = os.path.splitext(os.path.split(fullname)[1])[0]
    srcext = os.path.splitext(fullname)[1]
    shortname = srcname[3:]

    print('Обработка %s' % srcname + srcext)

    if diagonals:
        nplt, p2plt, p3plt, p4plt, p6plt, oplt, ISOCollect, corners = pasterise(fullname, True, 'no_diagonals')
        npltd, p2pltd, p3pltd, p4pltd, p6pltd, opltd, ISODiagCollect, corners = pasterise(fullname, True, 'diagonals')
    else:
        nplt, p2plt, p3plt, p4plt, p6plt, oplt, ISOCollect, corners = pasterise(fullname, True, 'none')

    n_file = donedir + '\\' + shortname + 'n' + srcext
    p_file = donedir + '\\' + shortname + 'p' + srcext
    c_file = donedir + '\\' + shortname + 'c' + srcext
    o_file = donedir + '\\' + shortname + 'o' + srcext

    if separate:
        if combine:
            slot_fullname = slot_srcdir + '\\' + srcname + '_slot' + srcext
            if os.path.exists(slot_fullname):
                slot_nplt, slot_p2plt, slot_p3plt, slot_p4plt, slot_p6plt, slot_oplt, *a = pasterise(slot_fullname,
                                                                                                     False, 'none')
                os.remove(slot_fullname)
                if nplt != 'PU':
                    with open(n_file, 'w') as outfile:
                        outfile.write(nplt)
                if slot_p2plt == 'PU': slot_p2plt = ''
                if slot_p3plt == 'PU': slot_p3plt = ''
                if slot_p4plt == 'PU': slot_p4plt = ''
                if slot_p6plt == 'PU': slot_p6plt = ''
                if p2plt == 'PU': p2plt = ''
                if p3plt == 'PU': p3plt = ''
                if p4plt == 'PU': p4plt = ''
                if p6plt == 'PU': p6plt = ''
                cplt = slot_p2plt + slot_p3plt + slot_p4plt + slot_p6plt + p2plt + p3plt + p4plt + p6plt
                pplt = p2plt + p3plt + p4plt + p6plt
                if pplt != 'PU':
                    with open(p_file, 'w') as outfile:
                        outfile.write(pplt)
                        outfile.close()
                if cplt != 'PU':
                    with open(c_file, 'w') as outfile:
                        outfile.write(cplt)
                        outfile.close()
                if oplt != 'PU':
                    with open(o_file, 'w') as outfile:
                        outfile.write(oplt)
                        outfile.close()
            else:
                FError(slot_fullname)
        else:
            extname = ''
            if nplt != 'PU':
                with open(n_file, 'w') as outfile:
                    outfile.write(nplt)
                    outfile.close()
                if makeISO:
                    ISOOut = make_iso(ISOCollect[0], corners[0], corners[1], corners[2], corners[3], ISOEtchSpeed, True)
                    with open((iso_donedir) + '\\' + shortname + 'n.iso', 'w') as outfile:
                        outfile.write(ISOOut)
                        outfile.close()
            if p2plt != 'PU':
                extname += 'p'
                with open(donedir + '\\' + shortname + extname + srcext, 'w') as outfile:
                    outfile.write(p2plt)
                    outfile.close()
                if makeISO:
                    ISOOut = make_iso(ISOCollect[1], corners[0], corners[1], corners[2], corners[3], ISORulesSpeed,
                                      True)
                    with open((iso_donedir) + '\\' + shortname + extname + '.iso', 'w') as outfile:
                        outfile.write(ISOOut)
                        outfile.close()
            if diagonals:
                if p2pltd != 'PU':
                    with open(donedir + '\\' + shortname + extname + 'd' + srcext, 'w') as outfile:
                        outfile.write(p2pltd)
                        outfile.close()
            if p3plt != 'PU':
                extname += 'p'
                with open(donedir + '\\' + shortname + extname + srcext, 'w') as outfile:
                    outfile.write(p3plt)
                    outfile.close()
                if makeISO:
                    ISOOut = make_iso(ISOCollect[2], corners[0], corners[1], corners[2], corners[3], ISORulesSpeed,
                                      True)
                    with open((iso_donedir) + '\\' + shortname + extname + '.iso', 'w') as outfile:
                        outfile.write(ISOOut)
                        outfile.close()
            if diagonals:
                if p3pltd != 'PU':
                    with open(donedir + '\\' + shortname + extname + 'd' + srcext, 'w') as outfile:
                        outfile.write(p3pltd)
                        outfile.close()
            if p4plt != 'PU':
                extname += 'p'
                with open(donedir + '\\' + shortname + extname + srcext, 'w') as outfile:
                    outfile.write(p4plt)
                    outfile.close()
                if makeISO:
                    ISOOut = make_iso(ISOCollect[3], corners[0], corners[1], corners[2], corners[3], ISORulesSpeed,
                                      True)
                    with open((iso_donedir) + '\\' + shortname + extname + '.iso', 'w') as outfile:
                        outfile.write(ISOOut)
                        outfile.close()
            if diagonals:
                if p4pltd != 'PU':
                    with open(donedir + '\\' + shortname + extname + 'd' + srcext, 'w') as outfile:
                        outfile.write(p4pltd)
                        outfile.close()
            if p6plt != 'PU':
                extname += 'p'
                with open(donedir + '\\' + shortname + extname + srcext, 'w') as outfile:
                    outfile.write(p6plt)
                    outfile.close()
                if makeISO:
                    ISOOut = make_iso(ISOCollect[4], corners[0], corners[1], corners[2], corners[3], ISORulesSpeed,
                                      True)
                    with open((iso_donedir) + '\\' + shortname + extname + '.iso', 'w') as outfile:
                        outfile.write(ISOOut)
                        outfile.close()
            if diagonals:
                if p6pltd != 'PU':
                    with open(donedir + '\\' + shortname + extname + 'd' + srcext, 'w') as outfile:
                        outfile.write(p6pltd)
                        outfile.close()
            if oplt != 'PU':
                with open(o_file, 'w') as outfile:
                    outfile.write(oplt)
                    outfile.close()
                if makeISO:
                    ISOOut = make_iso(ISOCollect[-1], corners[0], corners[1], corners[2], corners[3], ISOWoodSpeed,
                                      False)
                    with open((iso_donedir) + '\\' + shortname + 'o.iso', 'w') as outfile:
                        outfile.write(ISOOut)
                        outfile.close()
    else:
        if oplt != 'PU':
            with open(donedir + '\\' + srcname + srcext, 'w') as outfile:
                outfile.write(oplt)
                outfile.close()
    os.remove(fullname)
    time.sleep(1)
