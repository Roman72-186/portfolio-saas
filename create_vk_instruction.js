const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, AlignmentType, HeadingLevel, LevelFormat, BorderStyle, WidthType, ShadingType, Table, TableRow, TableCell, Header, Footer, PageNumber, ExternalHyperlink } = require("docx");

const tableBorder = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const cellBorders = { top: tableBorder, bottom: tableBorder, left: tableBorder, right: tableBorder };
const headerShading = { fill: "2B5797", type: ShadingType.CLEAR };
const altShading = { fill: "F2F7FB", type: ShadingType.CLEAR };

function hdr(text) {
  return new TableCell({
    borders: cellBorders, shading: headerShading,
    width: { size: 3120, type: WidthType.DXA },
    children: [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 80 }, children: [new TextRun({ text, bold: true, color: "FFFFFF", font: "Arial", size: 22 })] })]
  });
}

function cell(text, shade) {
  const opts = { borders: cellBorders, width: { size: 3120, type: WidthType.DXA }, children: [new Paragraph({ spacing: { before: 60, after: 60 }, children: [new TextRun({ text, font: "Arial", size: 21 })] })] };
  if (shade) opts.shading = altShading;
  return new TableCell(opts);
}

function p(text, opts = {}) {
  const runOpts = { text, font: "Arial", size: 22, ...opts.run };
  const parOpts = { spacing: { before: opts.before || 0, after: opts.after || 120 }, children: [new TextRun(runOpts)] };
  if (opts.align) parOpts.alignment = opts.align;
  return new Paragraph(parOpts);
}

function bold(text, opts = {}) {
  return p(text, { ...opts, run: { bold: true, ...opts.run } });
}

function runs(textRuns, opts = {}) {
  return new Paragraph({
    spacing: { before: opts.before || 0, after: opts.after || 120 },
    children: textRuns.map(r => typeof r === "string" ? new TextRun({ text: r, font: "Arial", size: 22 }) : new TextRun({ font: "Arial", size: 22, ...r }))
  });
}

function empty() {
  return new Paragraph({ spacing: { after: 60 }, children: [] });
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal",
        run: { size: 48, bold: true, color: "2B5797", font: "Arial" },
        paragraph: { spacing: { before: 0, after: 200 }, alignment: AlignmentType.CENTER } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, color: "2B5797", font: "Arial" },
        paragraph: { spacing: { before: 360, after: 160 } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, color: "404040", font: "Arial" },
        paragraph: { spacing: { before: 240, after: 120 } } },
    ]
  },
  numbering: {
    config: [
      { reference: "steps", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "steps2", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "steps3", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "steps4", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "steps5", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "steps6", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  sections: [{
    properties: {
      page: { margin: { top: 1134, right: 1134, bottom: 1134, left: 1134 } }
    },
    headers: {
      default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "Инструкция для заказчика", font: "Arial", size: 18, color: "999999", italics: true })] })] })
    },
    footers: {
      default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Страница ", font: "Arial", size: 18, color: "999999" }), new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 18, color: "999999" }), new TextRun({ text: " из ", font: "Arial", size: 18, color: "999999" }), new TextRun({ children: [PageNumber.TOTAL_PAGES], font: "Arial", size: 18, color: "999999" })] })] })
    },
    children: [
      // === TITLE ===
      new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun("Настройка входа через ВКонтакте")] }),
      p("Пошаговая инструкция для получения ID приложения и защищённого ключа", { align: AlignmentType.CENTER, run: { color: "666666", italics: true }, after: 300 }),

      // === ЧТО НУЖНО ПОЛУЧИТЬ ===
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Что нужно получить")] }),
      p("Чтобы на сайте заработал вход через ВКонтакте и проверка участия в закрытой группе, нам нужны 3 вещи от вас:"),
      p("Важно: саму проверку участия в группе сайт делает через access_token и ID группы. ID приложения и защищённый ключ нужны для безопасного получения этого access_token при входе через ВК.", { after: 180 }),

      new Table({
        columnWidths: [3120, 3120, 3120],
        rows: [
          new TableRow({ tableHeader: true, children: [hdr("Что это"), hdr("Как выглядит"), hdr("Где взять")] }),
          new TableRow({ children: [cell("ID приложения"), cell("Число, например: 52145678"), cell("Настройки приложения ВК")] }),
          new TableRow({ children: [cell("Защищённый ключ (секретный ключ)", true), cell("Набор букв и цифр", true), cell("Настройки приложения ВК", true)] }),
          new TableRow({ children: [cell("ID вашей группы"), cell("Число, например: 123456789"), cell("Адрес группы ВК")] }),
        ]
      }),

      runs([{ text: "Адрес возврата ", bold: true }, "известен заранее, но его нужно указать в настройках приложения, как показано ниже."]),
      empty(),

      // === ШАГ 1 ===
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Шаг 1. Создаём приложение VK ID")] }),
      p("Приложение VK ID \u2014 это запись в системе ВКонтакте, которая разрешает вашему сайту использовать вход через ВК. Создаётся бесплатно."),

      new Paragraph({ numbering: { reference: "steps", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Откройте в браузере: ", font: "Arial", size: 22 }), new TextRun({ text: "dev.vk.com/ru/admin/connect-auth", font: "Arial", size: 22, bold: true, color: "2B5797" })] }),
      new Paragraph({ numbering: { reference: "steps", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Если ссылка не открылась, зайдите на ", font: "Arial", size: 22 }), new TextRun({ text: "dev.vk.com", font: "Arial", size: 22, bold: true, color: "2B5797" }), new TextRun({ text: " и откройте создание приложения для авторизации", font: "Arial", size: 22 })] }),
      new Paragraph({ numbering: { reference: "steps", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Нажмите кнопку ", font: "Arial", size: 22 }), new TextRun({ text: "\u00ABСоздать приложение\u00BB", font: "Arial", size: 22, bold: true })] }),
      new Paragraph({ numbering: { reference: "steps", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "В поле ", font: "Arial", size: 22 }), new TextRun({ text: "Название", font: "Arial", size: 22, bold: true }), new TextRun({ text: " \u2014 напишите что угодно, например: ", font: "Arial", size: 22 }), new TextRun({ text: "Портфолио Студентов", font: "Arial", size: 22, italics: true })] }),
      new Paragraph({ numbering: { reference: "steps", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "В поле ", font: "Arial", size: 22 }), new TextRun({ text: "Платформа", font: "Arial", size: 22, bold: true }), new TextRun({ text: " \u2014 выберите ", font: "Arial", size: 22 }), new TextRun({ text: "Web", font: "Arial", size: 22, bold: true })] }),
      new Paragraph({ numbering: { reference: "steps", level: 0 }, spacing: { after: 200 }, children: [new TextRun({ text: "Подтвердите создание приложения", font: "Arial", size: 22 })] }),

      runs([{ text: "Готово! ", bold: true }, "Вы попадёте на страницу настроек нового приложения."]),
      empty(),

      // === ШАГ 2 ===
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Шаг 2. Настраиваем авторизацию")] }),
      p("На странице приложения найдите раздел \u00ABПодключение авторизации\u00BB или блок с настройками авторизации. Заполните поля:"),

      new Paragraph({ numbering: { reference: "steps2", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Базовый домен", font: "Arial", size: 22, bold: true }), new TextRun({ text: " \u2014 впишите:  ", font: "Arial", size: 22 }), new TextRun({ text: "apparchi.ru", font: "Arial", size: 22, bold: true, color: "2B5797" })] }),
      new Paragraph({ numbering: { reference: "steps2", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Доверенный Redirect URL", font: "Arial", size: 22, bold: true }), new TextRun({ text: " \u2014 впишите:  ", font: "Arial", size: 22 }), new TextRun({ text: "https://apparchi.ru/auth/vk/callback", font: "Arial", size: 22, bold: true, color: "2B5797" })] }),

      p("Нажмите \u00ABСохранить\u00BB или \u00ABГотово\u00BB.", { before: 120 }),
      empty(),

      // === ШАГ 3 ===
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Шаг 3. Копируем ключи")] }),
      p("После сохранения вы увидите два важных поля. Скопируйте их значения:"),

      new Paragraph({ numbering: { reference: "steps3", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "ID приложения", font: "Arial", size: 22, bold: true }), new TextRun({ text: " \u2014 это число вверху страницы (например: 52145678). Скопируйте его.", font: "Arial", size: 22 })] }),
      new Paragraph({ numbering: { reference: "steps3", level: 0 }, spacing: { after: 200 }, children: [new TextRun({ text: "Защищённый ключ", font: "Arial", size: 22, bold: true }), new TextRun({ text: " (или \u00ABСекретный ключ\u00BB) \u2014 набор букв и цифр. Если скрыт звёздочками, нажмите \u00ABПоказать\u00BB. Скопируйте его.", font: "Arial", size: 22 })] }),

      runs([{ text: "\u26A0 Важно: ", bold: true, color: "CC0000" }, "секретный ключ нельзя отправлять в открытых чатах и группах. Отправьте его разработчику в личном сообщении."]),
      empty(),

      // === ШАГ 4 ===
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Шаг 4. Узнаём ID вашей группы ВК")] }),
      p("Откройте вашу группу ВКонтакте в браузере и посмотрите на адресную строку."),
      empty(),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Если адрес содержит цифры:")] }),
      runs(["Например: ", { text: "vk.com/club", bold: true }, { text: "123456789", bold: true, color: "2B5797" }]),
      runs(["Цифры после слова \u00ABclub\u00BB \u2014 это и есть ID группы. В этом примере: ", { text: "123456789", bold: true }]),
      empty(),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Если адрес содержит текст (короткое имя):")] }),
      runs(["Например: ", { text: "vk.com/my_beauty_club", bold: true }]),
      p("В таком случае просто отправьте разработчику ссылку на группу. Числовой ID мы определим сами."),
      runs(["Например: ", { text: "vk.com/my_beauty_club", bold: true, color: "2B5797" }]),
      empty(),

      // === ШАГ 5 ===
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Шаг 5. Отправьте данные разработчику")] }),
      p("Отправьте разработчику в личном сообщении эти три значения:"),
      empty(),

      new Table({
        columnWidths: [4680, 4680],
        rows: [
          new TableRow({ tableHeader: true, children: [
            new TableCell({ borders: cellBorders, shading: headerShading, width: { size: 4680, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 80 }, children: [new TextRun({ text: "Что", bold: true, color: "FFFFFF", font: "Arial", size: 22 })] })] }),
            new TableCell({ borders: cellBorders, shading: headerShading, width: { size: 4680, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 80 }, children: [new TextRun({ text: "Ваше значение", bold: true, color: "FFFFFF", font: "Arial", size: 22 })] })] }),
          ] }),
          new TableRow({ children: [
            new TableCell({ borders: cellBorders, width: { size: 4680, type: WidthType.DXA }, children: [new Paragraph({ spacing: { before: 80, after: 80 }, children: [new TextRun({ text: "ID приложения", font: "Arial", size: 22, bold: true })] })] }),
            new TableCell({ borders: cellBorders, width: { size: 4680, type: WidthType.DXA }, children: [new Paragraph({ spacing: { before: 80, after: 80 }, children: [new TextRun({ text: "(впишите сюда)", font: "Arial", size: 22, color: "999999", italics: true })] })] }),
          ] }),
          new TableRow({ children: [
            new TableCell({ borders: cellBorders, width: { size: 4680, type: WidthType.DXA }, shading: altShading, children: [new Paragraph({ spacing: { before: 80, after: 80 }, children: [new TextRun({ text: "Защищённый ключ", font: "Arial", size: 22, bold: true })] })] }),
            new TableCell({ borders: cellBorders, width: { size: 4680, type: WidthType.DXA }, shading: altShading, children: [new Paragraph({ spacing: { before: 80, after: 80 }, children: [new TextRun({ text: "(впишите сюда)", font: "Arial", size: 22, color: "999999", italics: true })] })] }),
          ] }),
          new TableRow({ children: [
            new TableCell({ borders: cellBorders, width: { size: 4680, type: WidthType.DXA }, children: [new Paragraph({ spacing: { before: 80, after: 80 }, children: [new TextRun({ text: "ID группы ВК", font: "Arial", size: 22, bold: true })] })] }),
            new TableCell({ borders: cellBorders, width: { size: 4680, type: WidthType.DXA }, children: [new Paragraph({ spacing: { before: 80, after: 80 }, children: [new TextRun({ text: "(впишите сюда)", font: "Arial", size: 22, color: "999999", italics: true })] })] }),
          ] }),
        ]
      }),
      empty(),
      empty(),

      // === КАК ЭТО РАБОТАЕТ ===
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Как это будет работать")] }),
      p("После того, как вы передадите данные, на сайте появится кнопка \u00ABВойти через ВКонтакте\u00BB. Вот что будет происходить:"),

      new Paragraph({ numbering: { reference: "steps6", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Студент нажимает кнопку \u00ABВойти через ВК\u00BB на сайте", font: "Arial", size: 22 })] }),
      new Paragraph({ numbering: { reference: "steps6", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Открывается страница ВКонтакте, где студент входит в аккаунт и подтверждает доступ", font: "Arial", size: 22 })] }),
      new Paragraph({ numbering: { reference: "steps6", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "ВКонтакте возвращает пользователя обратно на сайт", font: "Arial", size: 22 })] }),
      new Paragraph({ numbering: { reference: "steps6", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Сервер сайта получает временный код и обменивает его на access_token с помощью ID приложения и защищённого ключа", font: "Arial", size: 22 })] }),
      new Paragraph({ numbering: { reference: "steps6", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "После этого сайт автоматически проверяет: состоит ли студент в вашей группе ВК?", font: "Arial", size: 22 })] }),
      new Paragraph({ numbering: { reference: "steps6", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Если да \u2014 студент попадает в личный кабинет", font: "Arial", size: 22, bold: true })] }),
      new Paragraph({ numbering: { reference: "steps6", level: 0 }, spacing: { after: 200 }, children: [new TextRun({ text: "Если нет \u2014 видит сообщение \u00ABВы не являетесь участником клуба\u00BB", font: "Arial", size: 22 })] }),

      runs([{ text: "То есть: ", bold: true }, "вход будет только для участников вашей группы ВК. Никто посторонний не попадёт."]),
      empty(),

      // === ВАЖНО ===
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Важные моменты")] }),

      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Создание приложения ВК бесплатное", font: "Arial", size: 22, bold: true }), new TextRun({ text: " \u2014 никакой оплаты не требуется", font: "Arial", size: 22 })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Защищённый ключ \u2014 конфиденциальный", font: "Arial", size: 22, bold: true }), new TextRun({ text: " \u2014 не публикуйте его нигде, отправьте только разработчику лично", font: "Arial", size: 22 })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 100 }, children: [new TextRun({ text: "Если смените домен сайта", font: "Arial", size: 22, bold: true }), new TextRun({ text: " \u2014 нужно будет обновить адрес в настройках приложения ВК", font: "Arial", size: 22 })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 200 }, children: [new TextRun({ text: "Если ВК попросит дополнительную проверку", font: "Arial", size: 22, bold: true }), new TextRun({ text: " \u2014 сроки зависят от ВК и статуса вашего аккаунта разработчика", font: "Arial", size: 22 })] }),

      // === ЧАСТЫЕ ВОПРОСЫ ===
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Частые вопросы")] }),

      bold("У меня уже есть приложение ВК. Можно его использовать?", { before: 120 }),
      p("Да, если это приложение для авторизации с платформой Web и в него можно добавить Redirect URL: https://apparchi.ru/auth/vk/callback"),

      bold("Что если студент не состоит в группе?", { before: 120 }),
      p("Он увидит сообщение: \u00ABВы не являетесь участником клуба. Вступите в группу и попробуйте снова.\u00BB"),

      bold("Что именно нужно разработчику?", { before: 120 }),
      p("Обычно достаточно трёх значений: ID приложения, защищённый ключ и ID вашей группы ВК. Дальше сайт сам получит access_token и выполнит проверку участия в группе."),

      bold("Я случайно удалил приложение. Что делать?", { before: 120 }),
      p("Создайте новое по этой же инструкции и передайте разработчику новые данные."),
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  const path = "C:/Users/User/Desktop/Портфолио в N8N/portfolio-saas/Инструкция_ВК_для_заказчика.docx";
  fs.writeFileSync(path, buffer);
  console.log("Created: " + path);
});
