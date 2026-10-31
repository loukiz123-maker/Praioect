"use strict";

// These translations cover application-owned interface text, not player text,
// administrator drafts, rule quotations, or the API's raw JSON. Keep the
// Russian source strings stable so backend status/error messages can be mapped.
(() => {
  // Translation arrays follow the interface-language order: English, Kazakh, Uzbek.
  const messages = {
    "Перейти к форме обращения": [
      "Skip to the ticket form",
      "Өтініш формасына өту",
      "Murojaat formasiga o‘tish",
    ],
    НАВИГАЦИЯ: ["NAVIGATION", "НАВИГАЦИЯ", "NAVIGATSIYA"],
    Разбор: ["Triage", "Талдау", "Tahlil"],
    Очередь: ["Queue", "Кезек", "Navbat"],
    Админка: ["Admin", "Әкімші", "Admin paneli"],
    СПРАВКА: ["HELP", "АНЫҚТАМА", "MA’LUMOT"],
    "О помощнике": [
      "About the assistant",
      "Көмекші туралы",
      "Yordamchi haqida",
    ],
    "Решение — за человеком": [
      "People make the decision",
      "Шешімді адам қабылдайды",
      "Qarorni inson qabul qiladi",
    ],
    "Помощник готовит черновик. Окончательное решение принимает администратор.":
      [
        "The assistant prepares a draft. An administrator makes the final decision.",
        "Көмекші жауап жобасын дайындайды. Соңғы шешімді әкімші қабылдайды.",
        "Yordamchi qoralama tayyorlaydi. Yakuniy qarorni administrator qabul qiladi.",
      ],
    "Центр поддержки": [
      "Support center",
      "Қолдау орталығы",
      "Qo‘llab-quvvatlash markazi",
    ],
    "Новое обращение": ["New ticket", "Жаңа өтініш", "Yangi murojaat"],
    "Язык интерфейса": [
      "Interface language",
      "Интерфейс тілі",
      "Interfeys tili",
    ],
    "Язык автоответа": [
      "Automatic reply language",
      "Автожауап тілі",
      "Avtomatik javob tili",
    ],
    "По языку игрока (авто)": [
      "Player's language (auto)",
      "Ойыншы тіліне сай (авто)",
      "O‘yinchi tilida (avto)",
    ],
    "Выбор меняет новый черновик, а не сообщение игрока. Цитаты правил остаются в оригинале.":
      [
        "This choice changes the new draft, not the player's message. Rule quotations remain in their original language.",
        "Таңдалған тіл ойыншының хабарламасын емес, жаңа жауап жобасын өзгертеді. Ереже дәйексөздері түпнұсқа тілінде қалады.",
        "Tanlov o‘yinchi xabarini emas, yangi qoralamani o‘zgartiradi. Qoidalardan iqtiboslar asl tilda qoladi.",
      ],
    "Локальный шаблон, не нейросеть. Проверьте ответ; цитаты правил остаются в оригинале.":
      [
        "Local template, not a neural network. Check the reply; rule quotations remain in their original language.",
        "Жергілікті үлгі, нейрожелі емес. Жауапты тексеріңіз; ереже дәйексөздері түпнұсқа тілінде қалады.",
        "Mahalliy shablon, neyrotarmoq emas. Javobni tekshiring; qoida iqtiboslari asl tilda qoladi.",
      ],
    "Создать черновик": ["Create draft", "Жоба жасау", "Qoralama yaratish"],
    "Заменить текущую правку ответом администратора?": [
      "Replace the current edit with the administrator's reply?",
      "Ағымдағы түзетуді әкімші жауабымен ауыстыру керек пе?",
      "Joriy tahrirni administrator javobi bilan almashtirasizmi?",
    ],
    "Заменить текущий текст новым черновиком? Несохранённые правки будут потеряны.":
      [
        "Replace the current text with a new draft? Unsaved edits will be lost.",
        "Ағымдағы мәтінді жаңа жобамен ауыстыру керек пе? Сақталмаған түзетулер жоғалады.",
        "Joriy matnni yangi qoralama bilan almashtirasizmi? Saqlanmagan tahrirlar yo‘qoladi.",
      ],
    "Черновик создан локально. Проверьте и сохраните его; игроку он не отправлен.":
      [
        "The draft was created locally. Check and save it; it has not been sent to the player.",
        "Жоба жергілікті түрде жасалды. Оны тексеріп, сақтаңыз; ойыншыға жіберілген жоқ.",
        "Qoralama mahalliy yaratildi. Uni tekshirib saqlang; u o‘yinchiga yuborilmagan.",
      ],
    "Автоматический черновик недоступен. Напишите ответ вручную.": [
      "The automatic draft is unavailable. Write the reply manually.",
      "Автоматты жауап жобасы қолжетімсіз. Жауапты қолмен жазыңыз.",
      "Avtomatik qoralama mavjud emas. Javobni qo‘lda yozing.",
    ],
    "Не удалось создать черновик. Попробуйте ещё раз.": [
      "Could not create a draft. Please try again.",
      "Жоба жасау мүмкін болмады. Қайталап көріңіз.",
      "Qoralama yaratilmadi. Qaytadan urinib ko‘ring.",
    ],
    "Нет связи с сервером. Черновик не создан.": [
      "Cannot reach the server. The draft was not created.",
      "Серверге қосылу мүмкін емес. Жоба жасалған жоқ.",
      "Server bilan aloqa yo‘q. Qoralama yaratilmadi.",
    ],
    "Выберите язык ответа: автоматически, RU, EN, KK или UZ.": [
      "Choose a reply language: automatic, RU, EN, KK, or UZ.",
      "Жауап тілін таңдаңыз: автоматты, RU, EN, KK немесе UZ.",
      "Javob tilini tanlang: avtomatik, RU, EN, KK yoki UZ.",
    ],
    "Неверный язык черновика ответа.": [
      "Invalid draft language.",
      "Жауап жобасының тілі қате.",
      "Javob qoralamasi tili noto‘g‘ri.",
    ],
    "Неверные параметры создания черновика.": [
      "Invalid draft request parameters.",
      "Жобаны жасау параметрлері қате.",
      "Qoralama yaratish parametrlari noto‘g‘ri.",
    ],
    "Выберите язык ответа: RU, EN, KK или UZ.": [
      "Choose a reply language: RU, EN, KK, or UZ.",
      "Жауап тілін таңдаңыз: RU, EN, KK немесе UZ.",
      "Javob tilini tanlang: RU, EN, KK yoki UZ.",
    ],
    "Ответ на узбекском": [
      "Draft in Uzbek",
      "Өзбекше жауап жобасы",
      "O‘zbekcha javob",
    ],
    "Обращение изменилось. Обновите карточку перед созданием черновика.": [
      "The ticket changed. Refresh the card before creating a draft.",
      "Өтініш өзгерді. Жобаны жасамас бұрын карточканы жаңартыңыз.",
      "Murojaat o‘zgartirilgan. Qoralama yaratishdan oldin kartochkani yangilang.",
    ],
    "Исходный черновик изменился. Проверьте обращение и напишите ответ вручную.":
      [
        "The original draft has changed. Review the ticket and write a reply manually.",
        "Бастапқы жоба өзгерді. Өтінішті тексеріп, жауапты қолмен жазыңыз.",
        "Asl qoralama o‘zgargan. Murojaatni tekshirib, javobni qo‘lda yozing.",
      ],
    "Проверяем соединение": [
      "Checking connection",
      "Байланыс тексерілуде",
      "Ulanish tekshirilmoqda",
    ],
    "Демо-предпросмотр админки без отдельного входа. Используйте только тестовые данные.":
      [
        "Admin demo preview without a separate login. Use test data only.",
        "Әкімші панелінің жеке кірусіз демо-нұсқасы. Тек сынақ деректерін пайдаланыңыз.",
        "Admin panelining alohida kirishsiz demo ko‘rinishi. Faqat sinov ma’lumotlaridan foydalaning.",
      ],
    "База знаний не подключена. Поиск инструкций недоступен; черновики требуют проверки администратором.":
      [
        "The knowledge base is not connected. Instructions cannot be searched; drafts require administrator review.",
        "Білім базасы қосылмаған. Нұсқауларды іздеу қолжетімсіз; жауап жобаларын әкімші тексеруі керек.",
        "Bilimlar bazasi ulanmagan. Yo‘riqnomalarni qidirib bo‘lmaydi; qoralamalarni administrator tekshirishi kerak.",
      ],
    "Разбор обращения": [
      "Ticket triage",
      "Өтінішті талдау",
      "Murojaatni tahlil qilish",
    ],
    "Помощник подготовит черновик ответа с опорой на правила игры.": [
      "The assistant will prepare a reply draft based on the game rules.",
      "Көмекші ойын ережелеріне сүйеніп, жауап жобасын дайындайды.",
      "Yordamchi o‘yin qoidalariga asoslanib javob qoralamasini tayyorlaydi.",
    ],
    "Окончательное решение всегда за администратором": [
      "The administrator always makes the final decision",
      "Соңғы шешімді әрқашан әкімші қабылдайды",
      "Yakuniy qarorni har doim administrator qabul qiladi",
    ],
    "Локальная обработка": [
      "Local processing",
      "Жергілікті өңдеу",
      "Mahalliy ishlov berish",
    ],
    "Без сторонних API": [
      "No external APIs",
      "Сыртқы API қолданылмайды",
      "Tashqi API-larsiz",
    ],
    "Обращения в сессии": [
      "Tickets this session",
      "Сессиядағы өтініштер",
      "Sessiyadagi murojaatlar",
    ],
    обращений: ["tickets", "өтініш", "murojaat"],
    "Требуют проверки": ["Need review", "Тексеру қажет", "Tekshirish kerak"],
    черновиков: ["drafts", "жоба", "qoralama"],
    "Пункты правил": ["Rule clauses", "Ереже тармақтары", "Qoida bandlari"],
    пунктов: ["clauses", "тармақ", "band"],
    ВХОДЯЩЕЕ: ["INCOMING", "КІРІС", "KIRUVCHI"],
    "Добавьте сообщение игрока, чтобы начать разбор.": [
      "Add the player's message to start triage.",
      "Талдауды бастау үшін ойыншының хабарламасын қосыңыз.",
      "Tahlilni boshlash uchun o‘yinchi xabarini kiriting.",
    ],
    "Тип обращения": ["Ticket type", "Өтініш түрі", "Murojaat turi"],
    "Жалоба на игрока": [
      "Player complaint",
      "Ойыншыға шағым",
      "O‘yinchidan shikoyat",
    ],
    "Репорт из игры": [
      "In-game report",
      "Ойын ішіндегі өтініш",
      "O‘yindan yuborilgan murojaat",
    ],
    "Сообщение игрока": [
      "Player message",
      "Ойыншы хабарламасы",
      "O‘yinchi xabari",
    ],
    "Языки: RU, KK, UZ, EN, ES, PT": [
      "Languages: RU, KK, UZ, EN, ES, PT",
      "Тілдер: RU, KK, UZ, EN, ES, PT",
      "Tillar: RU, KK, UZ, EN, ES, PT",
    ],
    "0 символов": ["0 characters", "0 таңба", "0 belgi"],
    "Количество вложений": [
      "Number of attachments",
      "Тіркемелер саны",
      "Ilovalar soni",
    ],
    "Только число. Файлы не открываются.": [
      "Count only. Files are not opened.",
      "Тек санын көрсетіңіз. Файлдар ашылмайды.",
      "Faqat soni. Fayllar ochilmaydi.",
    ],
    "Хеш заявителя": [
      "Reporter hash",
      "Өтініш берушінің хэші",
      "Murojaatchi xeshi",
    ],
    необязательно: ["optional", "міндетті емес", "ixtiyoriy"],
    "Не вводите личные данные.": [
      "Do not enter personal data.",
      "Жеке деректерді енгізбеңіз.",
      "Shaxsiy ma’lumotlarni kiritmang.",
    ],
    "Примеры для теста": [
      "Test examples",
      "Сынақ мысалдары",
      "Sinov uchun misollar",
    ],
    "Разобрать обращение": [
      "Analyze ticket",
      "Өтінішті талдау",
      "Murojaatni tahlil qilish",
    ],
    "Очистить форму": ["Clear form", "Форманы тазалау", "Formani tozalash"],
    "Обращения для проверки сохраняются на этом сервере; во внешние API данные не отправляются.":
      [
        "Tickets requiring review are stored on this server; data is not sent to external APIs.",
        "Тексерілетін өтініштер осы серверде сақталады; деректер сыртқы API-лерге жіберілмейді.",
        "Tekshiruv uchun murojaatlar shu serverda saqlanadi; ma’lumotlar tashqi API-larga yuborilmaydi.",
      ],
    РЕЗУЛЬТАТ: ["RESULT", "НӘТИЖЕ", "NATIJA"],
    "Разбор помощника": [
      "Assistant analysis",
      "Көмекші талдауы",
      "Yordamchi tahlili",
    ],
    "Категория, приоритет и черновик ответа.": [
      "Category, priority, and reply draft.",
      "Санат, басымдық және жауап жобасы.",
      "Toifa, ustuvorlik va javob qoralamasi.",
    ],
    "Здесь появится результат": [
      "The result will appear here",
      "Нәтиже осы жерде көрсетіледі",
      "Natija shu yerda ko‘rinadi",
    ],
    "Введите сообщение игрока или выберите один из примеров.": [
      "Enter a player's message or choose an example.",
      "Ойыншы хабарламасын енгізіңіз немесе мысал таңдаңыз.",
      "O‘yinchi xabarini kiriting yoki misollardan birini tanlang.",
    ],
    "ПОМОЩНИК ПОДДЕРЖКИ": [
      "SUPPORT ASSISTANT",
      "ҚОЛДАУ КӨМЕКШІСІ",
      "QO‘LLAB-QUVVATLASH YORDAMCHISI",
    ],
    "РАЗБОР 01": ["ANALYSIS 01", "ТАЛДАУ 01", "TAHLIL 01"],
    "Возможен спам или повтор": [
      "Possible spam or duplicate",
      "Спам немесе қайталану болуы мүмкін",
      "Spam yoki takror bo‘lishi mumkin",
    ],
    "Нужна проверка": ["Review needed", "Тексеру қажет", "Tekshirish kerak"],
    "Текст обращения": ["Ticket text", "Өтініш мәтіні", "Murojaat matni"],
    Категория: ["Category", "Санат", "Toifa"],
    Приоритет: ["Priority", "Басымдық", "Ustuvorlik"],
    Язык: ["Language", "Тіл", "Til"],
    "Черновик ответа": ["Reply draft", "Жауап жобасы", "Javob qoralamasi"],
    "Проверьте текст и при необходимости измените его.": [
      "Review the text and edit it if necessary.",
      "Мәтінді тексеріп, қажет болса өзгертіңіз.",
      "Matnni tekshiring va kerak bo‘lsa o‘zgartiring.",
    ],
    "Язык интерфейса не меняет сообщение игрока или черновик.": [
      "The interface language does not change the player's message or the draft.",
      "Интерфейс тілін өзгерту ойыншы хабарламасын немесе жауап жобасын өзгертпейді.",
      "Interfeys tili o‘yinchi xabarini yoki qoralamani o‘zgartirmaydi.",
    ],
    "Редактируемый черновик ответа": [
      "Editable reply draft",
      "Өңделетін жауап жобасы",
      "Tahrirlanadigan javob qoralamasi",
    ],
    "Сохранить правку": ["Save edit", "Түзетуді сақтау", "Tahrirni saqlash"],
    "Копировать текст": ["Copy text", "Мәтінді көшіру", "Matnni nusxalash"],
    "Пункты в исходном черновике": [
      "Clauses in the original draft",
      "Бастапқы жобадағы тармақтар",
      "Asl qoralamadagi bandlar",
    ],
    "После правок проверьте ссылки вручную.": [
      "Check the references manually after editing.",
      "Түзетуден кейін сілтемелерді қолмен тексеріңіз.",
      "Tahrirdan keyin havolalarni qo‘lda tekshiring.",
    ],
    Доказательства: ["Evidence", "Дәлелдер", "Dalillar"],
    "На что обратить внимание": [
      "Points to review",
      "Назар аударатын жайттар",
      "E’tibor beriladigan jihatlar",
    ],
    "Автоматический разбор не выполнен": [
      "Automatic analysis was not completed",
      "Автоматты талдау орындалмады",
      "Avtomatik tahlil bajarilmadi",
    ],
    "Категория, приоритет и черновик не определены. Обращение может проверить администратор вручную.":
      [
        "The category, priority, and draft could not be determined. An administrator can review this ticket manually.",
        "Санат, басымдық және жауап жобасы анықталмады. Әкімші өтінішті қолмен тексере алады.",
        "Toifa, ustuvorlik va qoralama aniqlanmadi. Administrator murojaatni qo‘lda tekshirishi mumkin.",
      ],
    "Проверка администратором": [
      "Administrator review",
      "Әкімшінің тексеруі",
      "Administrator tekshiruvi",
    ],
    "Открыть админку →": [
      "Open admin panel →",
      "Әкімші панелін ашу →",
      "Admin panelini ochish →",
    ],
    "Отправить администратору": [
      "Send to administrator",
      "Әкімшіге жіберу",
      "Administratorga yuborish",
    ],
    "Ответ администратора": [
      "Administrator reply",
      "Әкімші жауабы",
      "Administrator javobi",
    ],
    "Использовать в черновике": [
      "Use in draft",
      "Жобаға енгізу",
      "Qoralamada ishlatish",
    ],
    "Копировать ответ": ["Copy reply", "Жауапты көшіру", "Javobni nusxalash"],
    "Посмотреть JSON ответа": [
      "View response JSON",
      "Жауаптың JSON деректерін қарау",
      "Javobning JSON ma’lumotlarini ko‘rish",
    ],
    "ТЕКУЩАЯ СЕССИЯ": ["CURRENT SESSION", "АҒЫМДАҒЫ СЕССИЯ", "JORIY SESSIYA"],
    "Очередь обращений": [
      "Ticket queue",
      "Өтініштер кезегі",
      "Murojaatlar navbati",
    ],
    "Очередь и черновики сохраняются в этой вкладке при обновлении и переходе в админку. После закрытия вкладки они могут пропасть. Не используйте общий компьютер для личных данных.":
      [
        "The queue and drafts are kept in this tab when you reload or visit the admin panel. They may disappear when the tab is closed. Do not use a shared computer for personal data.",
        "Бетті жаңартқанда немесе әкімші панеліне өткенде кезек пен жобалар осы қойындыда сақталады. Қойынды жабылса, олар жоғалуы мүмкін. Жеке деректер үшін ортақ компьютерді пайдаланбаңыз.",
        "Sahifani yangilaganda va admin paneliga o‘tganda navbat va qoralamalar shu varaqda saqlanadi. Varaq yopilgandan keyin ular yo‘qolishi mumkin. Shaxsiy ma’lumotlar uchun umumiy kompyuterdan foydalanmang.",
      ],
    "0 обращений": ["0 tickets", "0 өтініш", "0 murojaat"],
    "Очистить очередь": ["Clear queue", "Кезекті тазалау", "Navbatni tozalash"],
    "Не удалось восстановить или сохранить очередь в браузере. При обновлении или переходе данные могут пропасть. Проверьте настройки и свободное место.":
      [
        "The queue could not be restored or saved in your browser. It may be lost if you reload or leave. Check your settings and available storage.",
        "Кезекті браузерде қалпына келтіру немесе сақтау мүмкін болмады. Бетті жаңартқанда немесе басқа бетке өткенде деректер жоғалуы мүмкін. Баптаулар мен бос орынды тексеріңіз.",
        "Brauzerda navbatni tiklash yoki saqlash imkoni bo‘lmadi. Yangilashda yoki boshqa sahifaga o‘tishda ma’lumotlar yo‘qolishi mumkin. Sozlamalar va bo‘sh joyni tekshiring.",
      ],
    "Разобранные обращения появятся здесь": [
      "Analyzed tickets will appear here",
      "Талданған өтініштер осында көрсетіледі",
      "Tahlil qilingan murojaatlar shu yerda paydo bo‘ladi",
    ],
    "Помощник, а не судья": [
      "An assistant, not a judge",
      "Көмекші, төреші емес",
      "Yordamchi, hakam emas",
    ],
    "Жалобы, платежи, блокировки и подозрения на взлом проверяет человек. Помощник видит только количество вложений, а не их содержимое. Ответы не отправляются автоматически.":
      [
        "A person reviews complaints, payments, bans, and suspected account compromise. The assistant sees only the number of attachments, not their contents. Replies are not sent automatically.",
        "Шағымдарды, төлемдерді, бұғаттауларды және аккаунт бұзылды деген күдікті адам тексереді. Көмекші тіркемелердің мазмұнын емес, тек санын көреді. Жауаптар автоматты түрде жіберілмейді.",
        "Shikoyatlar, to‘lovlar, bloklashlar va akkaunt buzilganiga oid shubhalarni inson tekshiradi. Yordamchi ilovalar mazmunini emas, faqat sonini ko‘radi. Javoblar avtomatik yuborilmaydi.",
      ],
    "Статус сервиса ↗": [
      "Service status ↗",
      "Сервис күйі ↗",
      "Xizmat holati ↗",
    ],

    // Jury-facing project and data-storage explanation.
    "Сервер не готов к публичному доступу. Данные организаторов и резервные копии нужно удалить в течение 14 дней после объявления победителей, если нет отдельного соглашения.":
      [
        "The server is not ready for public access. Organizer data and backups must be deleted within 14 days after the winners are announced, unless otherwise agreed.",
        "Сервер жалпыға қолжетімді пайдалануға дайын емес. Бөлек келісім болмаса, ұйымдастырушылардың деректері мен сақтық көшірмелерін жеңімпаздар жарияланғаннан кейін 14 күн ішінде жою керек.",
        "Server ommaviy foydalanishga tayyor emas. Alohida kelishuv bo‘lmasa, tashkilotchilar ma’lumotlari va zaxira nusxalarini g‘oliblar e’lon qilinganidan keyin 14 kun ichida o‘chirish kerak.",
      ],
    "При указанном хеше заявителя пятое похожее обращение за час отмечается как повтор. История сбрасывается при перезапуске сервиса.":
      [
        "When a reporter hash is provided, the fifth similar ticket within an hour is flagged as a duplicate. The history resets when the service restarts.",
        "Өтініш берушінің хэші көрсетілсе, бір сағаттағы бесінші ұқсас өтініш қайталану ретінде белгіленеді. Сервис қайта іске қосылғанда тарих өшіріледі.",
        "Murojaatchi xeshi ko‘rsatilsa, bir soat ichidagi beshinchi o‘xshash murojaat takror deb belgilanadi. Xizmat qayta ishga tushirilganda tarix tozalanadi.",
      ],
    "Распознанные платежи, апелляции блокировок и подозрения на взлом требуют проверки человеком. Внешних уведомлений нет: администратор самостоятельно проверяет очередь.":
      [
        "Recognized payments, ban appeals and suspected account compromise require human review. There are no external notifications: the administrator checks the queue independently.",
        "Анықталған төлем мәселелерін, бұғаттау апелляцияларын және аккаунт бұзылды деген күдікті адам тексеруі керек. Сыртқы хабарландырулар жоқ: әкімші кезекті өзі тексереді.",
        "Aniqlangan to‘lovlar, bloklash apellyatsiyalari va buzib kirish shubhalarini inson tekshirishi kerak. Tashqi bildirishnomalar yo‘q: administrator navbatni o‘zi tekshiradi.",
      ],
    "Как работает система": [
      "How it works",
      "Жүйе қалай жұмыс істейді",
      "Tizim qanday ishlaydi",
    ],
    "О ПРОЕКТЕ": ["ABOUT THE PROJECT", "ЖОБА ТУРАЛЫ", "LOYIHA HAQIDA"],
    "Как работает Support Copilot": [
      "How Support Copilot works",
      "Support Copilot қалай жұмыс істейді",
      "Support Copilot qanday ishlaydi",
    ],
    "Мы создали локальный веб-помощник на Python с интерфейсами оператора и администратора. Он помогает готовить ответы на обращения игроков, но не заменяет человека.":
      [
        "We built a local Python web assistant with operator and administrator interfaces. It helps prepare replies to player tickets, but does not replace a person.",
        "Біз оператор мен әкімші интерфейстері бар Python негізіндегі жергілікті веб-көмекші жасадық. Ол ойыншылардың өтініштеріне жауап дайындауға көмектеседі, бірақ адамды алмастырмайды.",
        "Biz operator va administrator interfeyslariga ega mahalliy Python veb-yordamchisini yaratdik. U o‘yinchilar murojaatlariga javob tayyorlashga yordam beradi, ammo inson o‘rnini bosmaydi.",
      ],
    "ЛОКАЛЬНЫЙ MVP": ["LOCAL MVP", "ЖЕРГІЛІКТІ MVP", "MAHALLIY MVP"],
    "Приём обращения": [
      "Receive a ticket",
      "Өтінішті қабылдау",
      "Murojaatni qabul qilish",
    ],
    "Оператор вводит сообщение игрока и число вложений. Сервис не открывает файлы и не видит содержимое скриншотов.":
      [
        "The operator enters the player's message and the number of attachments. The service does not open files or view screenshots.",
        "Оператор ойыншы хабарламасын және тіркемелер санын енгізеді. Сервис файлдарды ашпайды және скриншоттардың мазмұнын көрмейді.",
        "Operator o‘yinchi xabarini va ilovalar sonini kiritadi. Xizmat fayllarni ochmaydi va skrinshotlar mazmunini ko‘rmaydi.",
      ],
    "Разбор и черновик": [
      "Analysis and draft",
      "Талдау және жауап жобасы",
      "Tahlil va qoralama",
    ],
    "Локальные эвристики определяют язык, категорию, приоритет и возможный повтор, пытаются выделить ник, сервер и упомянутые правила. В черновик могут попасть найденные пункты: их релевантность проверяет человек, ссылки не придумываются. Предположения игрока не считаются фактами. Упоминание доказательств не подтверждает их наличие.":
      [
        "Local heuristics identify language, category, priority and possible duplicates, and try to extract the nickname, server and mentioned rules. Found clauses may be included in the draft: a person checks their relevance, and references are not invented. The player's claims are not treated as facts. Mentioning evidence does not prove it exists.",
        "Жергілікті эвристикалар тілді, санатты, басымдықты және ықтимал қайталануды анықтап, никті, серверді және аталған ережелерді табуға тырысады. Жауап жобасына табылған тармақтар қосылуы мүмкін: олардың сәйкестігін адам тексереді, сілтемелер ойдан шығарылмайды. Ойыншының болжамдары факт ретінде қабылданбайды. Дәлелдердің аталғаны олардың бар екенін растамайды.",
        "Mahalliy evristikalar tilni, toifani, ustuvorlikni va mumkin bo‘lgan takrorni aniqlaydi, nik, server va tilga olingan qoidalarni ajratishga urinadi. Qoralamaga topilgan bandlar kiritilishi mumkin: ularning mosligini inson tekshiradi, havolalar to‘qib chiqarilmaydi. O‘yinchi taxminlari fakt deb hisoblanmaydi. Dalillar tilga olinishi ularning mavjudligini tasdiqlamaydi.",
      ],
    "Проверка человеком": [
      "Human review",
      "Адамның тексеруі",
      "Inson tekshiruvi",
    ],
    "Обращения, требующие человека, и корректные обращения при сбое разбора направляются в админку, если очередь доступна. Любое обращение можно передать вручную; проверяйте подтверждение передачи.":
      [
        "Tickets requiring human review and valid tickets affected by an analysis failure are sent to the admin queue if it is available. Any ticket can also be sent manually; check that delivery is confirmed.",
        "Адамның тексеруі қажет өтініштер және талдау қатесіне ұшыраған жарамды өтініштер кезек қолжетімді болса, әкімші панеліне жіберіледі. Кез келген өтінішті қолмен жіберуге болады; жіберілгенін растауды тексеріңіз.",
        "Inson tekshiruvi zarur bo‘lgan murojaatlar hamda tahlil xatosida to‘g‘ri shakllangan murojaatlar, navbat mavjud bo‘lsa, admin paneliga yo‘naltiriladi. Istalgan murojaatni qo‘lda yuborish mumkin; yuborish tasdig‘ini tekshiring.",
      ],
    "Ответ оператору": [
      "Reply to the operator",
      "Операторға жауап",
      "Operatorga javob",
    ],
    "Администратор проверяет сведения, может исправить ответ, сохранить или эскалировать обращение и вернуть готовый текст оператору. Игроку ответ автоматически не отправляется.":
      [
        "The administrator reviews the details, can edit the reply, save or escalate the ticket, and return the completed text to the operator. It is not sent to the player automatically.",
        "Әкімші мәліметтерді тексереді, жауапты түзете алады, өтінішті сақтайды немесе қосымша тексеруге жібереді және дайын мәтінді операторға қайтарады. Жауап ойыншыға автоматты түрде жіберілмейді.",
        "Administrator ma’lumotlarni tekshiradi, javobni tuzatishi, murojaatni saqlashi yoki qo‘shimcha tekshiruvga yuborishi va tayyor matnni operatorga qaytarishi mumkin. Javob o‘yinchiga avtomatik yuborilmaydi.",
      ],
    "ХРАНЕНИЕ ДАННЫХ": [
      "DATA STORAGE",
      "ДЕРЕКТЕРДІ САҚТАУ",
      "MA’LUMOTLARNI SAQLASH",
    ],
    "Где сохраняются обращения": [
      "Where tickets are stored",
      "Өтініштер қайда сақталады",
      "Murojaatlar qayerda saqlanadi",
    ],
    "Очередь оператора и очередь администратора хранятся отдельно.": [
      "The operator and administrator queues are stored separately.",
      "Оператор мен әкімші кезектері бөлек сақталады.",
      "Operator navbati va administrator navbati alohida saqlanadi.",
    ],
    "Вкладка оператора": [
      "Operator's tab",
      "Оператор қойындысы",
      "Operator varag‘i",
    ],
    "Пока хранилище браузера (sessionStorage) доступно, в этой вкладке сохраняются обращения, форма, черновики и доступ к ответам. При обновлении и возвращении из админки они восстанавливаются, но после закрытия вкладки могут пропасть. Вкладки не синхронизируются; при ошибке хранения появится предупреждение.":
      [
        "While browser storage (sessionStorage) is available, this tab keeps tickets, the form, drafts and access to replies. They are restored after a reload or a return from the admin panel, but may disappear when the tab closes. Tabs do not sync; a warning appears if storage fails.",
        "Браузер жады (sessionStorage) қолжетімді кезде осы қойындыда өтініштер, форма, жауап жобалары және жауаптарға қолжетімділік сақталады. Бетті жаңартқанда немесе әкімші панелінен оралғанда олар қалпына келеді, бірақ қойынды жабылса, жоғалуы мүмкін. Қойындылар өзара синхрондалмайды; сақтау қатесі болса, ескерту көрсетіледі.",
        "Brauzer xotirasi (sessionStorage) mavjud bo‘lsa, murojaatlar, forma, qoralamalar va javoblarga kirish shu varaqda saqlanadi. Yangilaganda va admin panelidan qaytganda ular tiklanadi, ammo varaq yopilgach yo‘qolishi mumkin. Varaqlar sinxronlanmaydi; saqlashda xato bo‘lsa ogohlantirish chiqadi.",
      ],
    "Серверная очередь": ["Server queue", "Серверлік кезек", "Server navbati"],
    "В серверной очереди на базе SQLite сохраняются только обращения, направленные администратору. Подтверждённый статус означает, что запись получена. При обрыве подтверждение может потеряться даже после сохранения: проверьте админку или повторите передачу. Записи старше 14 дней удаляются при следующем обращении к очереди; администратор может удалить их раньше.":
      [
        "Only tickets sent to the administrator are saved in the SQLite server queue. A confirmed status means the record was received. If the connection drops, confirmation can be lost even after saving: check the admin panel or retry. Records older than 14 days are removed the next time the queue is accessed; an administrator can delete them earlier.",
        "SQLite негізіндегі серверлік кезекте тек әкімшіге жіберілген өтініштер сақталады. Расталған күй жазбаның қабылданғанын білдіреді. Байланыс үзілсе, жазба сақталса да растау жоғалуы мүмкін: әкімші панелін тексеріңіз немесе қайта жіберіңіз. 14 күннен асқан жазбалар кезекке келесі рет жүгінгенде жойылады; әкімші оларды ертерек өшіре алады.",
        "SQLite asosidagi server navbatida faqat administratorga yuborilgan murojaatlar saqlanadi. Tasdiqlangan holat yozuv qabul qilinganini bildiradi. Aloqa uzilganda, hatto saqlanganidan keyin ham tasdiq yo‘qolishi mumkin: admin panelini tekshiring yoki qayta yuboring. 14 kundan eski yozuvlar navbatga keyingi murojaatda o‘chiriladi; administrator ularni oldinroq o‘chirishi mumkin.",
      ],
    "Если данные вкладки и доступ к ответам утрачены, локальная очередь автоматически не восстановится с сервера. Переданные обращения остаются в админке до удаления. Очистка локальной очереди не удаляет серверные записи; форму нужно очистить отдельно.":
      [
        "If the tab's data and access to replies are lost, the local queue is not automatically restored from the server. Sent tickets remain in the admin panel until deleted. Clearing the local queue does not delete server records; clear the form separately.",
        "Қойынды деректері мен жауаптарға қолжетімділік жоғалса, жергілікті кезек серверден автоматты түрде қалпына келмейді. Жіберілген өтініштер жойылғанға дейін әкімші панелінде қалады. Жергілікті кезекті тазалау сервердегі жазбаларды жоймайды; форманы бөлек тазалау керек.",
        "Varaq ma’lumotlari va javoblarga kirish yo‘qolsa, mahalliy navbat serverdan avtomatik tiklanmaydi. Yuborilgan murojaatlar o‘chirilguncha admin panelida qoladi. Mahalliy navbatni tozalash serverdagi yozuvlarni o‘chirmaydi; formani alohida tozalash kerak.",
      ],
    "Языки и оригиналы": [
      "Languages and original content",
      "Тілдер және түпнұсқалар",
      "Tillar va asl matnlar",
    ],
    "Переключатель меняет только язык интерфейса. Текст игрока, готовые черновики, цитаты правил и исходный JSON не переводятся. Для нового автоответа можно отдельно выбрать русский, английский, казахский или узбекский; по умолчанию используется определённый язык игрока. Если он не определён, используется русский и требуется проверка.":
      [
        "The switch changes only the interface language. Player text, existing drafts, rule quotations and raw JSON are not translated. For a new automatic reply, you can separately choose Russian, English, Kazakh or Uzbek; the detected player language is used by default. If it is undetermined, Russian is used and review is required.",
        "Ауыстырғыш тек интерфейс тілін өзгертеді. Ойыншы мәтіні, дайын жауап жобалары, ереже дәйексөздері және бастапқы JSON аударылмайды. Жаңа автожауап үшін орыс, ағылшын, қазақ немесе өзбек тілін бөлек таңдауға болады; әдепкіде ойыншының анықталған тілі қолданылады. Тіл анықталмаса, орыс тілі қолданылады және тексеру қажет.",
        "O‘zgartirgich faqat interfeys tilini almashtiradi. O‘yinchi matni, tayyor qoralamalar, qoida iqtiboslari va asl JSON tarjima qilinmaydi. Yangi avtomatik javob uchun rus, ingliz, qozoq yoki o‘zbek tilini alohida tanlash mumkin; odatda o‘yinchining aniqlangan tili qo‘llanadi. Til aniqlanmasa, rus tili qo‘llanadi va tekshiruv talab etiladi.",
      ],
    "Границы прототипа": [
      "Prototype limitations",
      "Прототиптің шектеулері",
      "Prototip cheklovlari",
    ],
    "Это эвристический MVP без LLM и внешних API. Качество на реальных данных не измерено; оценка уверенности не равна точности. Факты и окончательное решение проверяет человек.":
      [
        "This is a heuristic MVP without an LLM or external APIs. Its quality on real data has not been measured; the confidence score is not accuracy. A person checks the facts and makes the final decision.",
        "Бұл LLM және сыртқы API қолданбайтын эвристикалық MVP. Нақты деректердегі сапасы өлшенбеген; сенімділік бағасы дәлдік көрсеткіші емес. Фактілерді адам тексереді және соңғы шешімді адам қабылдайды.",
        "Bu LLM va tashqi API-larsiz evristik MVP. Haqiqiy ma’lumotlardagi sifat o‘lchanmagan; ishonch bahosi aniqlik degani emas. Faktlarni inson tekshiradi va yakuniy qarorni qabul qiladi.",
      ],
    "В проверенной выборке из 1000 обращений нет меток категорий и приоритетов. Для подтверждения качества нужны ручная оценка, проверка цитат и база знаний.":
      [
        "The evaluated sample of 1,000 tickets has no category or priority labels. Human evaluation, citation review and a knowledge base are needed to confirm quality.",
        "Тексерілген 1000 өтініштің санаттары мен басымдықтары белгіленбеген. Сапаны растау үшін қолмен бағалау, дәйексөздерді тексеру және білім базасы қажет.",
        "Tekshirilgan 1000 ta murojaat to‘plamida toifa va ustuvorlik belgilari yo‘q. Sifatni tasdiqlash uchun qo‘lda baholash, iqtiboslarni tekshirish va bilimlar bazasi kerak.",
      ],
    "Обратная связь": ["Feedback", "Кері байланыс", "Fikr-mulohaza"],
    "Сохранённые правки администратора можно выгрузить в JSONL для будущей работы. Автоматического обучения нет. Выгрузка может содержать личные данные и требует приватного хранения.":
      [
        "Saved administrator edits can be exported as JSONL for future work. There is no automatic training. The export may contain personal data and must be kept private.",
        "Әкімшінің сақталған түзетулерін болашақ жұмыс үшін JSONL түрінде жүктеуге болады. Автоматты оқыту жоқ. Экспортта жеке деректер болуы мүмкін, сондықтан оны құпия сақтау қажет.",
        "Administratorning saqlangan tahrirlarini kelajakdagi ishlar uchun JSONL formatida yuklab olish mumkin. Avtomatik o‘qitish yo‘q. Yuklangan faylda shaxsiy ma’lumotlar bo‘lishi mumkin, uni maxfiy saqlash kerak.",
      ],
    Конфиденциальность: ["Privacy", "Құпиялылық", "Maxfiylik"],
    "Текст, черновики и доступ к ответам в браузере не шифруются. Не используйте общий компьютер. Удаление серверной записи не удаляет уже скачанные копии. Правки оператора видны администратору только после отдельной передачи.":
      [
        "Text, drafts and reply access in the browser are not encrypted. Do not use a shared computer. Deleting a server record does not delete downloaded copies. Operator edits are visible to the administrator only after being sent separately.",
        "Браузердегі мәтін, жобалар және жауаптарға қолжетімділік шифрланбайды. Ортақ компьютерді пайдаланбаңыз. Сервердегі жазбаны жою бұрын жүктелген көшірмелерді жоймайды. Оператор түзетулері бөлек жіберілгеннен кейін ғана әкімшіге көрінеді.",
        "Brauzerdagi matn, qoralamalar va javoblarga kirish shifrlanmaydi. Umumiy kompyuterdan foydalanmang. Serverdagi yozuvni o‘chirish oldin yuklab olingan nusxalarni o‘chirmaydi. Operator tahrirlari administratorga faqat alohida yuborilgandan keyin ko‘rinadi.",
      ],

    "Панель администратора — Grand Mobile": [
      "Admin panel — Grand Mobile",
      "Әкімші панелі — Grand Mobile",
      "Administrator paneli — Grand Mobile",
    ],
    "Перейти к содержимому": [
      "Skip to content",
      "Мазмұнға өту",
      "Asosiy tarkibga o‘tish",
    ],
    "РАБОЧЕЕ ПРОСТРАНСТВО": ["WORKSPACE", "ЖҰМЫС ОРНЫ", "ISH MAYDONI"],
    "Очередь проверки": ["Review queue", "Тексеру кезегі", "Tekshiruv navbati"],
    "К разбору обращений": [
      "Back to ticket triage",
      "Өтініштерді талдауға оралу",
      "Murojaatlar tahliliga",
    ],
    "Решение за вами": [
      "You make the decision",
      "Шешімді өзіңіз қабылдайсыз",
      "Qaror sizning qo‘lingizda",
    ],
    "Проверяйте факты и правила перед тем, как подготовить ответ.": [
      "Check the facts and rules before preparing a reply.",
      "Жауап дайындамас бұрын фактілер мен ережелерді тексеріңіз.",
      "Javob tayyorlashdan oldin faktlar va qoidalarni tekshiring.",
    ],
    Администратор: ["Administrator", "Әкімші", "Administrator"],
    "← К разбору": ["← Back to triage", "← Талдауға оралу", "← Tahlilga"],
    Выйти: ["Sign out", "Шығу", "Chiqish"],
    "Демо-предпросмотр без отдельного входа. Не используйте реальные данные в этом режиме.":
      [
        "Demo preview without a separate login. Do not use real data in this mode.",
        "Жеке кірусіз демо-нұсқа. Бұл режимде нақты деректерді пайдаланбаңыз.",
        "Alohida kirishsiz demo ko‘rinish. Bu rejimda haqiqiy ma’lumotlardan foydalanmang.",
      ],
    "ДОСТУП ДЛЯ АДМИНИСТРАТОРА": [
      "ADMINISTRATOR ACCESS",
      "ӘКІМШІГЕ АРНАЛҒАН ҚОЛЖЕТІМДІЛІК",
      "ADMINISTRATOR UCHUN KIRISH",
    ],
    "Вход в админку": [
      "Administrator sign in",
      "Әкімші панеліне кіру",
      "Admin paneliga kirish",
    ],
    "В очереди могут быть личные данные игроков. Введите ключ, чтобы открыть обращения.":
      [
        "The queue may contain players' personal data. Enter the key to open tickets.",
        "Кезекте ойыншылардың жеке деректері болуы мүмкін. Өтініштерді ашу үшін кілтті енгізіңіз.",
        "Navbatda o‘yinchilarning shaxsiy ma’lumotlari bo‘lishi mumkin. Murojaatlarni ochish uchun kalitni kiriting.",
      ],
    "Ключ доступа": ["Access key", "Қол жеткізу кілті", "Kirish kaliti"],
    "При первом запуске ключ создаётся в файле": [
      "On first launch, the key is created in",
      "Алғаш іске қосылғанда кілт мына файлда жасалады:",
      "Birinchi ishga tushirishda kalit",
    ],
    "на компьютере сервера. Не отправляйте его другим.": [
      "on the server computer. Do not share it.",
      "сервер компьютерінде. Оны басқа адамдарға жібермеңіз.",
      "faylida server kompyuterida yaratiladi. Uni boshqalarga yubormang.",
    ],
    "Открыть админку": [
      "Open admin panel",
      "Әкімші панелін ашу",
      "Admin panelini ochish",
    ],
    "← Вернуться к разбору": [
      "← Back to triage",
      "← Талдауға оралу",
      "← Tahlilga qaytish",
    ],
    "GRAND MOBILE / ПАНЕЛЬ АДМИНИСТРАТОРА": [
      "GRAND MOBILE / ADMIN PANEL",
      "GRAND MOBILE / ӘКІМШІ ПАНЕЛІ",
      "GRAND MOBILE / ADMINISTRATOR PANELI",
    ],
    "Рабочая очередь": ["Review workspace", "Жұмыс кезегі", "Ish navbati"],
    "Обращения, где нужна ваша проверка или автоматический разбор не сработал.":
      [
        "Tickets that need your review or could not be analyzed automatically.",
        "Сіздің тексеруіңіз қажет немесе автоматты талдау орындалмаған өтініштер.",
        "Sizning tekshiruvingiz kerak bo‘lgan yoki avtomatik tahlil bajarilmagan murojaatlar.",
      ],
    "Ручная проверка": ["Manual review", "Қолмен тексеру", "Qo‘lda tekshirish"],
    "Решение принимает человек": [
      "A person makes the decision",
      "Шешімді адам қабылдайды",
      "Qarorni inson qabul qiladi",
    ],
    "Ожидают проверки": [
      "Awaiting review",
      "Тексеруді күтуде",
      "Tekshiruv kutilmoqda",
    ],
    "В работе": ["In progress", "Қаралуда", "Jarayonda"],
    Эскалировано: [
      "Escalated",
      "Қосымша тексеруде",
      "Qo‘shimcha tekshiruvga yuborilgan",
    ],
    "Ответ подготовлен": ["Reply ready", "Жауап дайын", "Javob tayyorlandi"],
    "01 / ОБРАЩЕНИЯ": ["01 / TICKETS", "01 / ӨТІНІШТЕР", "01 / MUROJAATLAR"],
    "Обновляется автоматически.": [
      "Updates automatically.",
      "Автоматты түрде жаңартылады.",
      "Avtomatik yangilanadi.",
    ],
    Активные: ["Active", "Белсенді", "Faol"],
    Эскалации: ["Escalated", "Қосымша тексеру", "Qo‘shimcha tekshiruv"],
    Готовые: ["Resolved", "Дайын", "Tayyor"],
    Все: ["All", "Барлығы", "Barchasi"],
    "Загружаем очередь…": [
      "Loading queue…",
      "Кезек жүктелуде…",
      "Navbat yuklanmoqda…",
    ],
    "← Назад": ["← Previous", "← Алдыңғы", "← Orqaga"],
    "Вперёд →": ["Next →", "Келесі →", "Oldinga →"],
    "Записи старше 14 дней удаляются при следующем обращении к очереди. Данные хранятся только на этом сервере.":
      [
        "Entries older than 14 days are removed the next time the queue is accessed. Data is stored only on this server.",
        "14 күннен асқан жазбалар кезекке келесі рет жүгінгенде жойылады. Деректер тек осы серверде сақталады.",
        "14 kundan eski yozuvlar navbatga keyingi murojaatda o‘chiriladi. Ma’lumotlar faqat shu serverda saqlanadi.",
      ],
    "02 / ПРОВЕРКА": ["02 / REVIEW", "02 / ТЕКСЕРУ", "02 / TEKSHIRUV"],
    "Карточка обращения": [
      "Ticket details",
      "Өтініш карточкасы",
      "Murojaat kartochkasi",
    ],
    "Посмотрите детали и подготовьте ответ.": [
      "Review the details and prepare a reply.",
      "Мәліметтерді қарап, жауап дайындаңыз.",
      "Tafsilotlarni ko‘rib chiqing va javob tayyorlang.",
    ],
    "Выберите обращение": [
      "Select a ticket",
      "Өтінішті таңдаңыз",
      "Murojaatni tanlang",
    ],
    "Здесь будут текст игрока, причина передачи и черновик для вашей проверки.":
      [
        "The player's text, reason for review, and draft will appear here.",
        "Мұнда ойыншы мәтіні, тексеру себебі және жауап жобасы көрсетіледі.",
        "Bu yerda o‘yinchi matni, yuborish sababi va tekshirishingiz uchun qoralama bo‘ladi.",
      ],
    "Причина передачи": [
      "Reason for review",
      "Тексеруге жіберу себебі",
      "Yuborish sababi",
    ],
    Получено: ["Received", "Қабылданды", "Qabul qilindi"],
    "Почему нужна проверка": [
      "Why review is needed",
      "Тексеру не үшін қажет",
      "Nima uchun tekshiruv kerak",
    ],
    "Посмотреть черновик оператора": [
      "View operator draft",
      "Оператор жобасын қарау",
      "Operator qoralamasini ko‘rish",
    ],
    "Исправьте предложенный текст или напишите ответ самостоятельно.": [
      "Edit the suggested text or write your own reply.",
      "Ұсынылған мәтінді түзетіңіз немесе жауапты өзіңіз жазыңыз.",
      "Taklif qilingan matnni tuzating yoki javobni o‘zingiz yozing.",
    ],
    "Сохранённые правки учитываются как обратная связь. После отправки ответ появится оператору в его очереди; игроку он автоматически не отправляется.":
      [
        "Saved edits are recorded as feedback. After sending, the reply appears in the operator's queue; it is not sent to the player automatically.",
        "Сақталған түзетулер кері байланыс ретінде жазылады. Жібергеннен кейін жауап оператор кезегінде көрінеді; ол ойыншыға автоматты түрде жіберілмейді.",
        "Saqlangan tahrirlar fikr-mulohaza sifatida hisobga olinadi. Yuborilgandan keyin javob operatorning navbatida ko‘rinadi; u o‘yinchiga avtomatik yuborilmaydi.",
      ],
    "Отправить оператору": [
      "Send to operator",
      "Операторға жіберу",
      "Operatorga yuborish",
    ],
    "Сохранить черновик": ["Save draft", "Жобаны сақтау", "Qoralamani saqlash"],
    "Править ответ": ["Edit reply", "Жауапты түзету", "Javobni tahrirlash"],
    Эскалировать: [
      "Escalate",
      "Қосымша тексеруге жіберу",
      "Qo‘shimcha tekshiruvga yuborish",
    ],
    "Взять в работу": ["Start review", "Қарауға алу", "Ishga olish"],
    "Эскалация помечает обращение в этой очереди для дополнительной проверки. Отдельных уведомлений и назначений пока нет.":
      [
        "Escalation marks this ticket for additional review in this queue. Separate notifications and assignments are not available yet.",
        "Эскалация осы кезектегі өтінішті қосымша тексеруге белгілейді. Жеке хабарламалар мен тағайындаулар әзірге жоқ.",
        "Bu amal murojaatni ushbu navbatda qo‘shimcha tekshiruv uchun belgilaydi. Hozircha alohida bildirishnomalar va tayinlashlar yo‘q.",
      ],
    "Обновить карточку": [
      "Refresh ticket",
      "Карточканы жаңарту",
      "Kartochkani yangilash",
    ],
    "Удалить из очереди": [
      "Delete from queue",
      "Кезектен жою",
      "Navbatdan o‘chirish",
    ],
    "03 / ОБРАТНАЯ СВЯЗЬ": [
      "03 / FEEDBACK",
      "03 / КЕРІ БАЙЛАНЫС",
      "03 / FIKR-MULOHAZA",
    ],
    "Правки для будущего обучения": [
      "Edits for future training",
      "Болашақ оқытуға арналған түзетулер",
      "Kelajakda o‘qitish uchun tahrirlar",
    ],
    "Сохранено обращений с обратной связью:": [
      "Tickets with saved feedback:",
      "Кері байланысы сақталған өтініштер:",
      "Fikr-mulohaza saqlangan murojaatlar:",
    ],
    ". Черновики и подтверждённые ответы помечаются отдельно; обучение автоматически не запускается.":
      [
        ". Drafts and approved replies are marked separately; training does not start automatically.",
        ". Жобалар мен расталған жауаптар бөлек белгіленеді; оқыту автоматты түрде іске қосылмайды.",
        ". Qoralamalar va tasdiqlangan javoblar alohida belgilanadi; o‘qitish avtomatik boshlanmaydi.",
      ],
    "Выгрузка содержит текст обращений и ответов. Храните её приватно и удаляйте по правилам проекта.":
      [
        "The export contains ticket and reply text. Keep it private and delete it according to the project rules.",
        "Экспортта өтініштер мен жауаптардың мәтіні бар. Оны құпия сақтап, жоба ережелеріне сәйкес жойыңыз.",
        "Yuklanadigan faylda murojaat va javoblar matni mavjud. Uni maxfiy saqlang va loyiha qoidalariga ko‘ra o‘chiring.",
      ],
    "Скачать правки JSONL": [
      "Download feedback JSONL",
      "Түзетулерді JSONL түрінде жүктеу",
      "Tahrirlarni JSONL sifatida yuklab olish",
    ],
    "Администратор проверяет факты.": [
      "An administrator checks the facts.",
      "Фактілерді әкімші тексереді.",
      "Administrator faktlarni tekshiradi.",
    ],
    "Вложения не открываются, а отправка ответа в игру пока не подключена.": [
      "Attachments are not opened, and sending replies to the game is not connected yet.",
      "Тіркемелер ашылмайды, ал жауапты ойынға жіберу әлі қосылмаған.",
      "Ilovalar ochilmaydi, javobni o‘yinga yuborish esa hozircha ulanmagan.",
    ],

    "Grand Mobile Support Copilot, на главную": [
      "Grand Mobile Support Copilot, home",
      "Grand Mobile Support Copilot, басты бет",
      "Grand Mobile Support Copilot, bosh sahifaga",
    ],
    "Основная навигация": [
      "Main navigation",
      "Негізгі навигация",
      "Asosiy navigatsiya",
    ],
    "Панель администратора": [
      "Admin panel",
      "Әкімші панелі",
      "Administrator paneli",
    ],
    Справка: ["Help", "Анықтама", "Ma’lumot"],
    "Как это работает": [
      "How it works",
      "Қалай жұмыс істейді",
      "Bu qanday ishlaydi",
    ],
    "Статистика текущего сеанса": [
      "Current session statistics",
      "Ағымдағы сессия статистикасы",
      "Joriy sessiya statistikasi",
    ],
    "Например: игрок оскорбил меня в чате. У меня есть скриншот.": [
      "For example: a player insulted me in chat. I have a screenshot.",
      "Мысалы: ойыншы чатта мені қорлады. Менде скриншот бар.",
      "Masalan: o‘yinchi meni chatda haqorat qildi. Menda skrinshot bor.",
    ],
    "Для поиска повторов": [
      "For finding duplicates",
      "Қайталануларды іздеу үшін",
      "Takrorlarni qidirish uchun",
    ],
    "Навигация администратора": [
      "Administrator navigation",
      "Әкімші навигациясы",
      "Administrator navigatsiyasi",
    ],
    "Grand Mobile, к разбору обращений": [
      "Grand Mobile, back to ticket triage",
      "Grand Mobile, өтініштерді талдауға оралу",
      "Grand Mobile, murojaatlar tahliliga",
    ],
    "Статусы очереди": ["Queue statuses", "Кезек күйлері", "Navbat holatlari"],
    "Обновить очередь": [
      "Refresh queue",
      "Кезекті жаңарту",
      "Navbatni yangilash",
    ],
    "Фильтр очереди": ["Queue filter", "Кезек сүзгісі", "Navbat filtri"],

    Оскорбление: ["Insult", "Қорлау", "Haqorat"],
    "Читы и ПО": [
      "Cheats and software",
      "Читтер мен бағдарламалар",
      "Chitlar va dasturlar",
    ],
    "Урон и нарушение RP": [
      "Damage and RP violations",
      "Зиян келтіру және RP бұзу",
      "Zarar va RP qoidalarini buzish",
    ],
    Мошенничество: ["Fraud", "Алаяқтық", "Firibgarlik"],
    "Реклама / RMT": ["Advertising / RMT", "Жарнама / RMT", "Reklama / RMT"],
    "Жалоба на администратора": [
      "Complaint about an administrator",
      "Әкімшіге шағым",
      "Administratordan shikoyat",
    ],
    "Другая жалоба": ["Other complaint", "Басқа шағым", "Boshqa shikoyat"],
    "Неполная жалоба": [
      "Incomplete complaint",
      "Толық емес шағым",
      "To‘liq bo‘lmagan shikoyat",
    ],
    "Вопрос об игре": [
      "Game question",
      "Ойын туралы сұрақ",
      "O‘yin haqida savol",
    ],
    "Помощь в игре": ["In-game help", "Ойындағы көмек", "O‘yinda yordam"],
    "Жалоба в репорте": [
      "Complaint in a report",
      "Репорттағы шағым",
      "Murojaatdagi shikoyat",
    ],
    "Доступ к аккаунту": [
      "Account access",
      "Аккаунтқа кіру",
      "Akkauntga kirish",
    ],
    Платёж: ["Payment", "Төлем", "To‘lov"],
    "Уточнение вопроса": [
      "Request for clarification",
      "Сұрақты нақтылау",
      "Savolni aniqlashtirish",
    ],
    Русский: ["Russian", "Орысша", "Rus tili"],
    Қазақша: ["Kazakh", "Қазақша", "Qozoq tili"],
    Казахский: ["Kazakh", "Қазақ тілі", "Qozoq tili"],
    Узбекский: ["Uzbek", "Өзбек тілі", "O‘zbek tili"],
    Английский: ["English", "Ағылшын тілі", "Ingliz tili"],
    Испанский: ["Spanish", "Испан тілі", "Ispan tili"],
    Португальский: ["Portuguese", "Португал тілі", "Portugal tili"],
    "Не определён": ["Undetermined", "Анықталмаған", "Aniqlanmagan"],
    Критический: ["Critical", "Өте жоғары", "Kritik"],
    Высокий: ["High", "Жоғары", "Yuqori"],
    Обычный: ["Normal", "Қалыпты", "Odatdagi"],
    Низкий: ["Low", "Төмен", "Past"],
    "P0 · критический": ["P0 · critical", "P0 · өте жоғары", "P0 · kritik"],
    "P1 · высокий": ["P1 · high", "P1 · жоғары", "P1 · yuqori"],
    "P2 · обычный": ["P2 · normal", "P2 · қалыпты", "P2 · odatdagi"],
    "P3 · низкий": ["P3 · low", "P3 · төмен", "P3 · past"],
    "Игрок Alex_Nova оскорблял меня и мою семью в игровом чате. У меня есть скриншот.":
      [
        "Player Alex_Nova insulted me and my family in the game chat. I have a screenshot.",
        "Alex_Nova ойыншысы ойын чатында мені және отбасымды қорлады. Менде скриншот бар.",
        "O‘yinchi Alex_Nova o‘yin chatida meni va oilamni haqorat qildi. Menda skrinshot bor.",
      ],
    "Оплатил покупку, но внутриигровая валюта не поступила. Что делать?": [
      "I paid for a purchase, but the in-game currency did not arrive. What should I do?",
      "Сатып алу үшін төледім, бірақ ойын валютасы түскен жоқ. Не істеуім керек?",
      "Xarid uchun to‘lov qildim, lekin o‘yin valyutasi kelmadi. Nima qilishim kerak?",
    ],

    "Ответ готов": ["Reply ready", "Жауап дайын", "Javob tayyor"],
    Ожидает: ["Waiting", "Күтуде", "Kutilmoqda"],
    "Доп. проверка": [
      "Further review",
      "Қосымша тексеру",
      "Qo‘shimcha tekshiruv",
    ],
    "У администратора": ["With administrator", "Әкімшіде", "Administratorda"],
    "Нет подтверждения": ["Not confirmed", "Расталмады", "Tasdiq yo‘q"],
    "Можно уточнить": [
      "Clarification possible",
      "Нақтылауға болады",
      "Aniqlashtirish mumkin",
    ],
    "Обращение ещё не передано администратору.": [
      "This ticket has not yet been sent to an administrator.",
      "Өтініш әкімшіге әлі жіберілген жоқ.",
      "Murojaat hali administratorga yuborilmagan.",
    ],
    "Если заметили ошибку, отправьте обращение на ручную проверку.": [
      "If you notice an error, send the ticket for manual review.",
      "Қате байқасаңыз, өтінішті қолмен тексеруге жіберіңіз.",
      "Xatoni sezsangiz, murojaatni qo‘lda tekshirishga yuboring.",
    ],
    "Обращение в очереди администратора. Ожидает проверки.": [
      "The ticket is in the administrator's queue, awaiting review.",
      "Өтініш әкімші кезегінде, тексеруді күтуде.",
      "Murojaat administrator navbatida. Tekshiruv kutilmoqda.",
    ],
    "Администратор пометил обращение для дополнительной проверки.": [
      "The administrator marked this ticket for further review.",
      "Әкімші өтінішті қосымша тексеруге белгіледі.",
      "Administrator murojaatni qo‘shimcha tekshiruv uchun belgiladi.",
    ],
    "Администратор взял обращение в работу.": [
      "The administrator has started reviewing this ticket.",
      "Әкімші өтінішті қарауға алды.",
      "Administrator murojaatni ishga oldi.",
    ],
    "Ответ появится здесь, пока доступна очередь в этой вкладке. Игроку он автоматически не отправляется.":
      [
        "The reply will appear here while this tab's queue is available. It is not sent to the player automatically.",
        "Осы қойындыдағы кезек қолжетімді болғанда жауап осында көрінеді. Ол ойыншыға автоматты түрде жіберілмейді.",
        "Bu varaqdagi navbat mavjud ekan, javob shu yerda ko‘rinadi. U o‘yinchiga avtomatik yuborilmaydi.",
      ],
    "Передать правку администратору": [
      "Send edit to administrator",
      "Түзетуді әкімшіге жіберу",
      "Tahrirni administratorga yuborish",
    ],
    "Передано администратору": [
      "Sent to administrator",
      "Әкімшіге жіберілді",
      "Administratorga yuborildi",
    ],
    "Администратор подготовил ответ.": [
      "The administrator prepared a reply.",
      "Әкімші жауап дайындады.",
      "Administrator javob tayyorladi.",
    ],
    "Проверьте текст. Автоматической отправки игроку нет.": [
      "Review the text. It is not sent to the player automatically.",
      "Мәтінді тексеріңіз. Ол ойыншыға автоматты түрде жіберілмейді.",
      "Matnni tekshiring. O‘yinchiga avtomatik yuborilmaydi.",
    ],
    "Проверка завершена": [
      "Review complete",
      "Тексеру аяқталды",
      "Tekshiruv tugadi",
    ],
    "Не удалось подтвердить передачу администратору.": [
      "Could not confirm delivery to the administrator.",
      "Әкімшіге жіберілгенін растау мүмкін болмады.",
      "Administratorga yuborilganini tasdiqlab bo‘lmadi.",
    ],
    "Проверьте сервер и очередь администратора либо повторите отправку. Без подтверждения не считайте обращение доставленным.":
      [
        "Check the server and administrator queue, or try sending again. Do not assume delivery without confirmation.",
        "Сервер мен әкімші кезегін тексеріңіз немесе қайта жіберіңіз. Растау болмаса, өтініш жеткізілді деп есептемеңіз.",
        "Serverni va administrator navbatini tekshiring yoki qayta yuboring. Tasdiqsiz murojaat yetkazildi deb hisoblamang.",
      ],
    "Повторить отправку": [
      "Retry sending",
      "Қайта жіберу",
      "Yuborishni takrorlash",
    ],
    "Запись проверки больше недоступна.": [
      "The review record is no longer available.",
      "Тексеру жазбасы енді қолжетімсіз.",
      "Tekshiruv yozuvi endi mavjud emas.",
    ],
    "Возможно, её удалили или истёк срок хранения. При необходимости отправьте обращение повторно.":
      [
        "It may have been deleted or expired. Send the ticket again if needed.",
        "Ол жойылған немесе сақтау мерзімі аяқталған болуы мүмкін. Қажет болса, өтінішті қайта жіберіңіз.",
        "U o‘chirilgan yoki saqlash muddati tugagan bo‘lishi mumkin. Zarur bo‘lsa, murojaatni qayta yuboring.",
      ],
    "Отправить повторно": ["Send again", "Қайта жіберу", "Qayta yuborish"],
    "Не удалось обновить статус. Проверьте соединение; последнее подтверждённое состояние показано выше.":
      [
        "Could not update the status. Check your connection; the last confirmed state is shown above.",
        "Күйді жаңарту мүмкін болмады. Байланысты тексеріңіз; соңғы расталған күй жоғарыда көрсетілген.",
        "Holatni yangilab bo‘lmadi. Ulanishni tekshiring; oxirgi tasdiqlangan holat yuqorida ko‘rsatilgan.",
      ],
    "Отправляем…": ["Sending…", "Жіберілуде…", "Yuborilmoqda…"],
    "Ответ администратора готов": [
      "Administrator reply ready",
      "Әкімшінің жауабы дайын",
      "Administrator javobi tayyor",
    ],
    "Нужна проверка человеком": [
      "Human review needed",
      "Адамның тексеруі қажет",
      "Inson tekshiruvi kerak",
    ],
    "Нужна проверка человеком.": [
      "Human review is needed.",
      "Адамның тексеруі қажет.",
      "Inson tekshiruvi kerak.",
    ],
    "Можно уточнить обращение.": [
      "The ticket can be clarified.",
      "Өтінішті нақтылауға болады.",
      "Murojaatni aniqlashtirish mumkin.",
    ],
    "Есть несохранённая правка": [
      "Unsaved edit",
      "Сақталмаған түзету бар",
      "Saqlanmagan tahrir bor",
    ],
    "Правка сохранена в этой вкладке": [
      "Edit saved in this tab",
      "Түзету осы қойындыда сақталды",
      "Tahrir shu varaqda saqlandi",
    ],
    "Нет подтверждённых": [
      "None confirmed",
      "Расталғаны жоқ",
      "Tasdiqlangani yo‘q",
    ],
    "Упомянуты или указаны в метаданных. Содержимое не проверено.": [
      "Mentioned or indicated in metadata. Contents have not been verified.",
      "Аталған немесе метадеректерде көрсетілген. Мазмұны тексерілген жоқ.",
      "Tilga olingan yoki metama’lumotlarda ko‘rsatilgan. Mazmuni tekshirilmagan.",
    ],
    "Не указаны": ["Not indicated", "Көрсетілмеген", "Ko‘rsatilmagan"],
    "Обнаружен возможный спам или дубликат.": [
      "Possible spam or duplicate detected.",
      "Спам немесе қайталану болуы мүмкін.",
      "Ehtimoliy spam yoki dublikat aniqlandi.",
    ],
    "Сервис вернул некорректный ответ.": [
      "The service returned an invalid response.",
      "Сервис қате жауап қайтарды.",
      "Xizmat noto‘g‘ri javob qaytardi.",
    ],
    "Не удалось передать обращение.": [
      "Could not submit the ticket.",
      "Өтінішті жіберу мүмкін болмады.",
      "Murojaatni yuborib bo‘lmadi.",
    ],
    "Не удалось подтвердить передачу обращения.": [
      "Could not confirm the ticket was submitted.",
      "Өтініштің жіберілгенін растау мүмкін болмады.",
      "Murojaat yuborilganini tasdiqlab bo‘lmadi.",
    ],
    "Введите текст обращения игрока.": [
      "Enter the player's ticket text.",
      "Ойыншы өтінішінің мәтінін енгізіңіз.",
      "O‘yinchi murojaati matnini kiriting.",
    ],
    "Количество вложений должно быть целым числом от 0 до 99.": [
      "The attachment count must be a whole number from 0 to 99.",
      "Тіркеме саны 0 мен 99 аралығындағы бүтін сан болуы керек.",
      "Ilovalar soni 0 dan 99 gacha bo‘lgan butun son bo‘lishi kerak.",
    ],
    "Браузер не поддерживает безопасную передачу. Обновите браузер.": [
      "Your browser does not support secure submission. Update your browser.",
      "Браузер қауіпсіз жіберуді қолдамайды. Браузерді жаңартыңыз.",
      "Brauzer xavfsiz yuborishni qo‘llab-quvvatlamaydi. Brauzerni yangilang.",
    ],
    "Разбираем…": ["Analyzing…", "Талдануда…", "Tahlil qilinmoqda…"],
    "Не удалось обработать обращение.": [
      "Could not process the ticket.",
      "Өтінішті өңдеу мүмкін болмады.",
      "Murojaatga ishlov berib bo‘lmadi.",
    ],
    "Автоматический разбор не выполнен. Проверьте состояние обращения в блоке результата.":
      [
        "Automatic analysis was not completed. Check the ticket status in the result panel.",
        "Автоматты талдау орындалмады. Нәтиже бөлімінде өтініш күйін тексеріңіз.",
        "Avtomatik tahlil bajarilmadi. Natija bo‘limida murojaat holatini tekshiring.",
      ],
    "Запись проверки больше недоступна. Правка осталась в этом окне; при необходимости отправьте обращение повторно.":
      [
        "The review record is no longer available. Your edit remains in this tab; send the ticket again if needed.",
        "Тексеру жазбасы енді қолжетімсіз. Түзету осы қойындыда қалды; қажет болса, өтінішті қайта жіберіңіз.",
        "Tekshiruv yozuvi endi mavjud emas. Tahrir shu oynada qoldi; kerak bo‘lsa, murojaatni qayta yuboring.",
      ],
    "Администратор подготовил ответ. Последняя правка не была передана и осталась в черновике.":
      [
        "The administrator prepared a reply. Your latest edit was not sent and remains in the draft.",
        "Әкімші жауап дайындады. Соңғы түзету жіберілген жоқ және жобада қалды.",
        "Administrator javob tayyorladi. Oxirgi tahrir yuborilmadi va qoralamada qoldi.",
      ],
    "Администратор подготовил ответ. Передачу последней правки подтвердить не удалось; сравните тексты.":
      [
        "The administrator prepared a reply. Delivery of your latest edit could not be confirmed; compare the texts.",
        "Әкімші жауап дайындады. Соңғы түзетудің жіберілгенін растау мүмкін болмады; мәтіндерді салыстырыңыз.",
        "Administrator javob tayyorladi. Oxirgi tahrir yuborilganini tasdiqlab bo‘lmadi; matnlarni solishtiring.",
      ],
    "Оператор запросил ручную проверку.": [
      "The operator requested a manual review.",
      "Оператор қолмен тексеруді сұрады.",
      "Operator qo‘lda tekshirishni so‘radi.",
    ],
    "Не удалось подтвердить обновление правки. Проверьте состояние обращения; текст остался в этом окне.":
      [
        "Could not confirm the edit was updated. Check the ticket status; the text remains in this tab.",
        "Түзетудің жаңартылғанын растау мүмкін болмады. Өтініш күйін тексеріңіз; мәтін осы қойындыда қалды.",
        "Tahrir yangilanganini tasdiqlab bo‘lmadi. Murojaat holatini tekshiring; matn shu oynada qoldi.",
      ],
    "Не удалось подтвердить передачу. Проверьте сервер и повторите отправку.": [
      "Could not confirm delivery. Check the server and try again.",
      "Жеткізілгенін растау мүмкін болмады. Серверді тексеріп, қайта жіберіңіз.",
      "Yuborilganini tasdiqlab bo‘lmadi. Serverni tekshirib, qayta yuboring.",
    ],
    "Текст скопирован": ["Text copied", "Мәтін көшірілді", "Matn nusxalandi"],
    "Текст выделен — скопируйте его": [
      "Text selected — copy it",
      "Мәтін белгіленді — оны көшіріңіз",
      "Matn belgilandi — uni nusxalang",
    ],
    "Правка сохранена только в этой вкладке": [
      "Edit saved only in this tab",
      "Түзету тек осы қойындыда сақталды",
      "Tahrir faqat shu varaqda saqlandi",
    ],
    "Ответ администратора вставлен; проверьте и сохраните правку в этой вкладке":
      [
        "Administrator reply inserted; review and save the edit in this tab",
        "Әкімші жауабы енгізілді; түзетуді тексеріп, осы қойындыда сақтаңыз",
        "Administrator javobi qo‘yildi; tahrirni tekshiring va shu varaqda saqlang",
      ],
    "Авторазбор недоступен": [
      "Automatic analysis unavailable",
      "Автоматты талдау қолжетімсіз",
      "Avtomatik tahlil mavjud emas",
    ],
    "Сервис работает": [
      "Service online",
      "Сервис жұмыс істеп тұр",
      "Xizmat ishlayapti",
    ],
    "Нет связи с сервисом": [
      "Service offline",
      "Сервиспен байланыс жоқ",
      "Xizmat bilan aloqa yo‘q",
    ],
    "Очистить очередь в этой вкладке? Черновики и доступ к ответам здесь будут удалены. Обращения, переданные администратору, останутся на сервере.":
      [
        "Clear the queue in this tab? Drafts and access to replies here will be removed. Tickets sent to the administrator will remain on the server.",
        "Осы қойындыдағы кезекті тазалау керек пе? Жобалар мен жауаптарға қолжетімділік жойылады. Әкімшіге жіберілген өтініштер серверде қалады.",
        "Shu varaqdagi navbatni tozalaysizmi? Bu yerdagi qoralamalar va javoblarga kirish o‘chiriladi. Administratorga yuborilgan murojaatlar serverda qoladi.",
      ],
    "Дождитесь завершения текущей операции перед переходом в админку.": [
      "Wait for the current operation to finish before opening the admin panel.",
      "Әкімші панеліне өтпес бұрын ағымдағы әрекеттің аяқталуын күтіңіз.",
      "Admin paneliga o‘tishdan oldin joriy amal tugashini kuting.",
    ],
    "Дождитесь завершения текущей операции перед очисткой очереди.": [
      "Wait for the current operation to finish before clearing the queue.",
      "Кезекті тазаламас бұрын ағымдағы әрекеттің аяқталуын күтіңіз.",
      "Navbatni tozalashdan oldin joriy amal tugashini kuting.",
    ],

    "Ошибка авторазбора": [
      "Automatic analysis failed",
      "Автоматты талдау қатесі",
      "Avtomatik tahlil xatosi",
    ],
    "Передано вручную": [
      "Sent manually",
      "Қолмен жіберілді",
      "Qo‘lda yuborilgan",
    ],
    Проверка: ["Review", "Тексеру", "Tekshiruv"],
    Неизвестно: ["Unknown", "Белгісіз", "Noma’lum"],
    "Сообщение не указано": [
      "No message provided",
      "Хабарлама көрсетілмеген",
      "Xabar ko‘rsatilmagan",
    ],
    "Сообщение не указано.": [
      "No message provided.",
      "Хабарлама көрсетілмеген.",
      "Xabar ko‘rsatilmagan.",
    ],
    "Сервер не ответил вовремя. Проверьте состояние операции.": [
      "The server did not respond in time. Check the operation status.",
      "Сервер уақытында жауап бермеді. Әрекеттің күйін тексеріңіз.",
      "Server vaqtida javob bermadi. Amal holatini tekshiring.",
    ],
    "Не удалось выполнить действие.": [
      "Could not complete the action.",
      "Әрекетті орындау мүмкін болмады.",
      "Amalni bajarib bo‘lmadi.",
    ],
    "Готовых ответов пока нет.": [
      "There are no completed replies yet.",
      "Әзірге дайын жауаптар жоқ.",
      "Hozircha tayyor javoblar yo‘q.",
    ],
    "Эскалированных обращений пока нет.": [
      "There are no escalated tickets yet.",
      "Әзірге қосымша тексеруге жіберілген өтініштер жоқ.",
      "Hozircha qo‘shimcha tekshiruvga yuborilgan murojaatlar yo‘q.",
    ],
    "В этом разделе пока нет обращений.": [
      "There are no tickets in this section yet.",
      "Бұл бөлімде әзірге өтініштер жоқ.",
      "Bu bo‘limda hozircha murojaatlar yo‘q.",
    ],
    "0 из 0": ["0 of 0", "0 / 0", "0 / 0"],
    "Карточка изменилась в другом окне. Обновите её перед сохранением; несохранённый текст не будет применён автоматически.":
      [
        "This ticket changed in another window. Refresh it before saving; unsaved text will not be applied automatically.",
        "Карточка басқа терезеде өзгертілді. Сақтамас бұрын оны жаңартыңыз; сақталмаған мәтін автоматты түрде қолданылмайды.",
        "Kartochka boshqa oynada o‘zgartirilgan. Saqlashdan oldin uni yangilang; saqlanmagan matn avtomatik qo‘llanmaydi.",
      ],
    "Нет связи с сервером. Не удалось обновить очередь.": [
      "No connection to the server. Could not refresh the queue.",
      "Сервермен байланыс жоқ. Кезекті жаңарту мүмкін болмады.",
      "Server bilan aloqa yo‘q. Navbatni yangilab bo‘lmadi.",
    ],
    "Не удалось обновить очередь.": [
      "Could not refresh the queue.",
      "Кезекті жаңарту мүмкін болмады.",
      "Navbatni yangilab bo‘lmadi.",
    ],
    "В метаданных указаны вложения; их содержимое недоступно.": [
      "Attachments are indicated in metadata; their contents are unavailable.",
      "Метадеректерде тіркемелер көрсетілген; олардың мазмұны қолжетімсіз.",
      "Metama’lumotlarda ilovalar ko‘rsatilgan; ularning mazmuni mavjud emas.",
    ],
    "Вложения в метаданных не указаны; текст игрока нужно проверить отдельно.":
      [
        "No attachments are indicated in metadata; the player's text must be checked separately.",
        "Метадеректерде тіркемелер көрсетілмеген; ойыншы мәтінін бөлек тексеру қажет.",
        "Metama’lumotlarda ilovalar ko‘rsatilmagan; o‘yinchi matnini alohida tekshirish kerak.",
      ],
    "Автоматический разбор не сработал или вернул некорректный результат. Категория и приоритет могут быть не определены.":
      [
        "Automatic analysis failed or returned an invalid result. Category and priority may be undetermined.",
        "Автоматты талдау орындалмады немесе қате нәтиже қайтарды. Санат пен басымдық анықталмаған болуы мүмкін.",
        "Avtomatik tahlil ishlamadi yoki noto‘g‘ri natija qaytardi. Toifa va ustuvorlik aniqlanmagan bo‘lishi mumkin.",
      ],
    "Оператор запросил дополнительную проверку.": [
      "The operator requested further review.",
      "Оператор қосымша тексеруді сұрады.",
      "Operator qo‘shimcha tekshiruvni so‘radi.",
    ],
    "Ответ необходимо проверить вручную.": [
      "The reply requires manual review.",
      "Жауапты қолмен тексеру қажет.",
      "Javobni qo‘lda tekshirish kerak.",
    ],
    "Ответ подготовлен и доступен оператору, пока доступна его очередь. Игроку он не отправлен.":
      [
        "The reply is ready and available to the operator while their queue is available. It has not been sent to the player.",
        "Жауап дайын және оператор кезегі қолжетімді болғанда көрінеді. Ол ойыншыға жіберілген жоқ.",
        "Javob tayyorlangan va operator navbati mavjud bo‘lsa, unga ko‘rinadi. U o‘yinchiga yuborilmagan.",
      ],
    "Обращение помечено для дополнительной проверки в общей очереди. Внешних уведомлений нет.":
      [
        "The ticket is marked for further review in the shared queue. No external notifications are sent.",
        "Өтініш ортақ кезекте қосымша тексеруге белгіленді. Сыртқы хабарламалар жіберілмейді.",
        "Murojaat umumiy navbatda qo‘shimcha tekshiruv uchun belgilangan. Tashqi bildirishnomalar yo‘q.",
      ],
    "Вернуть в работу": [
      "Return to review",
      "Қарауға қайтару",
      "Ishga qaytarish",
    ],
    "Сохранить и вернуть в работу": [
      "Save and return to review",
      "Сақтап, қарауға қайтару",
      "Saqlash va ishga qaytarish",
    ],
    "Обновить ответ оператору": [
      "Update reply for operator",
      "Операторға жауапты жаңарту",
      "Operatorga javobni yangilash",
    ],
    "Есть несохранённые правки. Перейти без сохранения?": [
      "You have unsaved edits. Continue without saving?",
      "Сақталмаған түзетулер бар. Сақтамай өту керек пе?",
      "Saqlanmagan tahrirlar bor. Saqlamasdan o‘tasizmi?",
    ],
    "Нет связи с сервером. Карточка не загружена.": [
      "No connection to the server. The ticket was not loaded.",
      "Сервермен байланыс жоқ. Карточка жүктелмеді.",
      "Server bilan aloqa yo‘q. Kartochka yuklanmadi.",
    ],
    "Не удалось открыть обращение.": [
      "Could not open the ticket.",
      "Өтінішті ашу мүмкін болмады.",
      "Murojaatni ochib bo‘lmadi.",
    ],
    "Вернуть готовый ответ в проверку? Он перестанет отображаться оператору как готовый. Уже скопированный текст отозвать нельзя.":
      [
        "Return this completed reply to review? It will no longer appear ready to the operator. Text already copied cannot be recalled.",
        "Дайын жауапты тексеруге қайтару керек пе? Ол операторға дайын жауап ретінде көрінбейді. Көшірілген мәтінді кері қайтару мүмкін емес.",
        "Tayyor javobni tekshiruvga qaytarasizmi? U operatorga tayyor sifatida ko‘rinmaydi. Oldin nusxalangan matnni qaytarib olib bo‘lmaydi.",
      ],
    "Добавьте текст ответа перед завершением проверки.": [
      "Add a reply before completing the review.",
      "Тексеруді аяқтамас бұрын жауап мәтінін енгізіңіз.",
      "Tekshiruvni yakunlashdan oldin javob matnini qo‘shing.",
    ],
    "Ответ доступен оператору в его очереди; игроку он не отправлен. Обратная связь сохранена.":
      [
        "The reply is available in the operator's queue; it was not sent to the player. Feedback was saved.",
        "Жауап оператор кезегінде қолжетімді; ол ойыншыға жіберілген жоқ. Кері байланыс сақталды.",
        "Javob operator navbatida unga ko‘rinadi; o‘yinchiga yuborilmagan. Fikr-mulohaza saqlandi.",
      ],
    "Черновик сохранён на сервере. Правки учитываются в обратной связи; ответ ещё не передан оператору как готовый.":
      [
        "The draft was saved on the server. Edits are recorded as feedback; the reply has not yet been sent to the operator as complete.",
        "Жоба серверде сақталды. Түзетулер кері байланыс ретінде жазылды; жауап операторға дайын деп әлі жіберілген жоқ.",
        "Qoralama serverda saqlandi. Tahrirlar fikr-mulohazada hisobga olinadi; javob hali operatorga tayyor deb yuborilmagan.",
      ],
    "Не удалось подтвердить сохранение. Скопируйте текст и обновите карточку.":
      [
        "Could not confirm the save. Copy your text and refresh the ticket.",
        "Сақталғанын растау мүмкін болмады. Мәтінді көшіріп, карточканы жаңартыңыз.",
        "Saqlanganini tasdiqlab bo‘lmadi. Matnni nusxalab, kartochkani yangilang.",
      ],
    "Не удалось подтвердить сохранение. Проверьте карточку.": [
      "Could not confirm the save. Check the ticket.",
      "Сақталғанын растау мүмкін болмады. Карточканы тексеріңіз.",
      "Saqlanganini tasdiqlab bo‘lmadi. Kartochkani tekshiring.",
    ],
    "Скопируйте свою правку, затем обновите карточку и проверьте её заново.": [
      "Copy your edit, then refresh and review the ticket again.",
      "Түзетуді көшіріп, карточканы жаңартып, қайта тексеріңіз.",
      "Tahriringizni nusxalang, so‘ng kartochkani yangilab, qayta tekshiring.",
    ],
    "Подготавливаем приватную выгрузку…": [
      "Preparing private export…",
      "Құпия экспорт дайындалуда…",
      "Maxfiy yuklama tayyorlanmoqda…",
    ],
    "Не удалось выгрузить обратную связь.": [
      "Could not export feedback.",
      "Кері байланысты экспорттау мүмкін болмады.",
      "Fikr-mulohazani yuklab bo‘lmadi.",
    ],
    "Не удалось проверить размер выгрузки.": [
      "Could not verify the export size.",
      "Экспорт көлемін тексеру мүмкін болмады.",
      "Yuklama hajmini tekshirib bo‘lmadi.",
    ],
    "Сохранённой обратной связи пока нет.": [
      "There is no saved feedback yet.",
      "Әзірге сақталған кері байланыс жоқ.",
      "Hozircha saqlangan fikr-mulohazalar yo‘q.",
    ],
    "Выгрузка прервана. Попробуйте ещё раз.": [
      "Export interrupted. Try again.",
      "Экспорт тоқтатылды. Қайталап көріңіз.",
      "Yuklash to‘xtatildi. Qaytadan urinib ko‘ring.",
    ],
    "Нет связи с сервером. Выгрузка не подготовлена.": [
      "No connection to the server. The export was not prepared.",
      "Сервермен байланыс жоқ. Экспорт дайындалмады.",
      "Server bilan aloqa yo‘q. Yuklama tayyorlanmadi.",
    ],
    "Не удалось подготовить выгрузку.": [
      "Could not prepare the export.",
      "Экспортты дайындау мүмкін болмады.",
      "Yuklamani tayyorlab bo‘lmadi.",
    ],
    "Удалить обращение, ответ и связанную обратную связь? Восстановить их будет нельзя. Уже скачанные копии нужно удалить отдельно.":
      [
        "Delete the ticket, reply, and associated feedback? They cannot be restored. Previously downloaded copies must be deleted separately.",
        "Өтінішті, жауапты және байланысты кері байланысты жою керек пе? Оларды қалпына келтіру мүмкін болмайды. Бұрын жүктелген көшірмелерді бөлек жою керек.",
        "Murojaat, javob va unga bog‘liq fikr-mulohazani o‘chirasizmi? Ularni tiklab bo‘lmaydi. Oldin yuklab olingan nusxalarni alohida o‘chirish kerak.",
      ],
    "Не удалось подтвердить удаление. Обновите очередь и проверьте статус.": [
      "Could not confirm deletion. Refresh the queue and check the status.",
      "Жойылғанын растау мүмкін болмады. Кезекті жаңартып, күйін тексеріңіз.",
      "O‘chirilganini tasdiqlab bo‘lmadi. Navbatni yangilang va holatni tekshiring.",
    ],
    "Не удалось подтвердить удаление. Проверьте очередь.": [
      "Could not confirm deletion. Check the queue.",
      "Жойылғанын растау мүмкін болмады. Кезекті тексеріңіз.",
      "O‘chirilganini tasdiqlab bo‘lmadi. Navbatni tekshiring.",
    ],
    "Введите ключ доступа администратора.": [
      "Enter the administrator access key.",
      "Әкімшінің қол жеткізу кілтін енгізіңіз.",
      "Administrator kirish kalitini kiriting.",
    ],
    "Нет связи с сервером. Проверьте, что он запущен.": [
      "No connection to the server. Check that it is running.",
      "Сервермен байланыс жоқ. Оның іске қосылғанын тексеріңіз.",
      "Server bilan aloqa yo‘q. Uning ishga tushirilganini tekshiring.",
    ],
    "Не удалось войти.": [
      "Could not sign in.",
      "Кіру мүмкін болмады.",
      "Kirib bo‘lmadi.",
    ],
    "Есть несохранённые правки. Выйти без сохранения?": [
      "You have unsaved edits. Sign out without saving?",
      "Сақталмаған түзетулер бар. Сақтамай шығу керек пе?",
      "Saqlanmagan tahrirlar bor. Saqlamasdan chiqasizmi?",
    ],
    "Есть несохранённые правки.": [
      "You have unsaved edits.",
      "Сақталмаған түзетулер бар.",
      "Saqlanmagan tahrirlar bor.",
    ],
    "Очередь администратора недоступна. Проверьте запуск сервера и папку данных.":
      [
        "The administrator queue is unavailable. Check the server and data folder.",
        "Әкімші кезегі қолжетімсіз. Сервер мен деректер қалтасын тексеріңіз.",
        "Administrator navbati mavjud emas. Server ishlashini va ma’lumotlar papkasini tekshiring.",
      ],

    "Платёжные обращения обязательно рассматривает человек.": [
      "Payment tickets must be reviewed by a person.",
      "Төлемге қатысты өтініштерді міндетті түрде адам қарайды.",
      "To‘lovga oid murojaatlarni albatta inson ko‘rib chiqadi.",
    ],
    "Вопросы аккаунта и возможного взлома требуют проверки человеком.": [
      "Account access and possible compromise require human review.",
      "Аккаунт пен ықтимал бұзылуға қатысты мәселелерді адам тексеруі керек.",
      "Akkaunt va ehtimoliy buzib kirish masalalarini inson tekshirishi kerak.",
    ],
    "Блокировки и апелляции рассматривает человек.": [
      "Bans and appeals are reviewed by a person.",
      "Бұғаттаулар мен апелляцияларды адам қарайды.",
      "Bloklashlar va apellyatsiyalarni inson ko‘rib chiqadi.",
    ],
    "Обстоятельства жалобы и решение по ней проверяет администратор.": [
      "An administrator reviews the complaint circumstances and decision.",
      "Шағым мән-жайын және ол бойынша шешімді әкімші тексереді.",
      "Shikoyat holatlarini va unga oid qarorni administrator tekshiradi.",
    ],
    "Категория требует участия администратора по таксономии.": [
      "This category requires administrator involvement under the taxonomy.",
      "Таксономия бойынша бұл санатқа әкімшінің қатысуы қажет.",
      "Taksonomiyaga ko‘ra bu toifa administrator ishtirokini talab qiladi.",
    ],
    "Метаданные указывают на вложения; их содержимое недоступно сервису.": [
      "Metadata indicates attachments; their contents are unavailable to the service.",
      "Метадеректер тіркемелер барын көрсетеді; олардың мазмұны сервиске қолжетімсіз.",
      "Metama’lumotlarda ilovalar ko‘rsatilgan; xizmat ularning mazmunini ko‘ra olmaydi.",
    ],
    "Игрок упомянул доказательства; их наличие и содержимое не подтверждены.": [
      "The player mentioned evidence; its existence and contents have not been verified.",
      "Ойыншы дәлелдерді атады; олардың бар-жоғы мен мазмұны расталмаған.",
      "O‘yinchi dalillarni tilga olgan; ularning mavjudligi va mazmuni tasdiqlanmagan.",
    ],
    "Релевантный пункт правила не подтверждён; черновик не готов к отправке.": [
      "A relevant rule clause has not been confirmed; the draft is not ready to send.",
      "Тиісті ереже тармағы расталмады; жауап жобасы жіберуге дайын емес.",
      "Tegishli qoida bandi tasdiqlanmagan; qoralama yuborishga tayyor emas.",
    ],
    "Подходящая статья базы знаний не подтверждена; черновик требует ручной проверки.":
      [
        "A relevant knowledge-base article has not been confirmed; the draft needs manual review.",
        "Тиісті білім базасы мақаласы расталмады; жауап жобасын қолмен тексеру қажет.",
        "Mos bilimlar bazasi maqolasi tasdiqlanmagan; qoralama qo‘lda tekshirilishi kerak.",
      ],
    "Язык не удалось уверенно определить; требуется проверка ответа.": [
      "The language could not be identified confidently; the reply requires review.",
      "Тілді сенімді анықтау мүмкін болмады; жауапты тексеру қажет.",
      "Tilni ishonchli aniqlab bo‘lmadi; javobni tekshirish kerak.",
    ],
    "Категория определена неуверенно.": [
      "The category was identified with low confidence.",
      "Санат төмен сенімділікпен анықталды.",
      "Toifa noaniq belgilandi.",
    ],
    "Похоже на пятое обращение того же игрока по той же проблеме за час.": [
      "This appears to be the same player's fifth ticket about the same issue within an hour.",
      "Бұл бір ойыншының бір мәселе бойынша бір сағаттағы бесінші өтінішіне ұқсайды.",
      "Bu bir soat ichida o‘sha o‘yinchining ayni muammo bo‘yicha beshinchi murojaatiga o‘xshaydi.",
    ],
    "Обнаружен признак автоматического или повторяющегося спама.": [
      "A sign of automated or repetitive spam was detected.",
      "Автоматты немесе қайталанатын спам белгісі анықталды.",
      "Avtomatik yoki takrorlanuvchi spam belgisi aniqlandi.",
    ],
    "Недостаточно информации, чтобы оценить суть и срочность обращения.": [
      "There is not enough information to assess the issue and its urgency.",
      "Өтініштің мәні мен шұғылдығын бағалау үшін ақпарат жеткіліксіз.",
      "Murojaat mazmuni va shoshilinchligini baholash uchun ma’lumot yetarli emas.",
    ],
    "Ответ и факты необходимо проверить администратору.": [
      "An administrator must review the reply and facts.",
      "Жауап пен фактілерді әкімші тексеруі қажет.",
      "Javob va faktlarni administrator tekshirishi kerak.",
    ],
    "Проверка человеком обязательна из-за риска или неуверенности.": [
      "Human review is mandatory due to risk or uncertainty.",
      "Тәуекелге немесе белгісіздікке байланысты адам тексеруі міндетті.",
      "Xavf yoki noaniqlik sababli inson tekshiruvi majburiy.",
    ],

    "Поле messages должно быть массивом сообщений": [
      "The messages field must be an array",
      "messages өрісі хабарламалар массиві болуы керек",
      "messages maydoni xabarlar massivi bo‘lishi kerak",
    ],
    "Поле server или region должно быть не длиннее 1024 символов.": [
      "The server or region field must be no longer than 1024 characters.",
      "server немесе region өрісі 1024 таңбадан аспауы керек.",
      "server yoki region maydoni 1024 ta belgidan oshmasligi kerak.",
    ],
    "Слишком много сообщений в обращении": [
      "Too many messages in the ticket",
      "Өтініштегі хабарламалар тым көп",
      "Murojaatda juda ko‘p xabar bor",
    ],
    "Необходимо хотя бы одно сообщение игрока (role: player)": [
      "At least one player message is required (role: player)",
      "Кемінде бір ойыншы хабарламасы қажет (role: player)",
      "Kamida bitta o‘yinchi xabari kerak (role: player)",
    ],
    "Запрос должен быть JSON-объектом": [
      "The request must be a JSON object",
      "Сұрау JSON нысаны болуы керек",
      "So‘rov JSON obyekti bo‘lishi kerak",
    ],
    "kind должен быть complaint или report": [
      "kind must be complaint or report",
      "kind мәні complaint немесе report болуы керек",
      "kind qiymati complaint yoki report bo‘lishi kerak",
    ],
    "Каждое сообщение должно быть объектом": [
      "Each message must be an object",
      "Әр хабарлама нысан болуы керек",
      "Har bir xabar obyekt bo‘lishi kerak",
    ],
    "Текст сообщения должен быть строкой": [
      "The message text must be a string",
      "Хабарлама мәтіні жол болуы керек",
      "Xabar matni satr bo‘lishi kerak",
    ],
    "Необходим корректный Content-Length": [
      "A valid Content-Length is required",
      "Жарамды Content-Length қажет",
      "To‘g‘ri Content-Length kerak",
    ],
    "Используйте Content-Type: application/json": [
      "Use Content-Type: application/json",
      "Content-Type: application/json қолданыңыз",
      "Content-Type: application/json dan foydalaning",
    ],
    "Нужен JSON-объект": [
      "A JSON object is required",
      "JSON нысаны қажет",
      "JSON obyekti kerak",
    ],
    "Неверная причина передачи": [
      "Invalid handoff reason",
      "Жіберу себебі қате",
      "Yuborish sababi noto‘g‘ri",
    ],
    "Результат разбора некорректен": [
      "Invalid analysis result",
      "Талдау нәтижесі қате",
      "Tahlil natijasi noto‘g‘ri",
    ],
    "Тело запроса должно быть корректным JSON в UTF-8": [
      "The request body must be valid UTF-8 JSON",
      "Сұрау мазмұны жарамды UTF-8 JSON болуы керек",
      "So‘rov tanasi UTF-8 formatidagi to‘g‘ri JSON bo‘lishi kerak",
    ],
    "Маршрут не найден": [
      "Route not found",
      "Маршрут табылмады",
      "Yo‘nalish topilmadi",
    ],
    "Неверные параметры списка обращений": [
      "Invalid ticket list parameters",
      "Өтініштер тізімінің параметрлері қате",
      "Murojaatlar ro‘yxati parametrlari noto‘g‘ri",
    ],
    "Ресурс не найден": [
      "Resource not found",
      "Ресурс табылмады",
      "Resurs topilmadi",
    ],
    "Неверный идентификатор проверки": [
      "Invalid review identifier",
      "Тексеру идентификаторы қате",
      "Tekshiruv identifikatori noto‘g‘ri",
    ],
    "Текст обращения должен быть корректным Unicode": [
      "The ticket text must be valid Unicode",
      "Өтініш мәтіні жарамды Unicode болуы керек",
      "Murojaat matni to‘g‘ri Unicode bo‘lishi kerak",
    ],
    "Черновик должен быть корректным Unicode": [
      "The draft must be valid Unicode",
      "Жоба жарамды Unicode болуы керек",
      "Qoralama to‘g‘ri Unicode bo‘lishi kerak",
    ],
    "Неверная причина передачи администратору": [
      "Invalid reason for administrator handoff",
      "Әкімшіге жіберу себебі қате",
      "Administratorga yuborish sababi noto‘g‘ri",
    ],
    "Неверный размер страницы": [
      "Invalid page size",
      "Бет өлшемі қате",
      "Sahifa o‘lchami noto‘g‘ri",
    ],
    "Результат должен быть корректным Unicode": [
      "The result must be valid Unicode",
      "Нәтиже жарамды Unicode болуы керек",
      "Natija to‘g‘ri Unicode bo‘lishi kerak",
    ],
    "Неверный ключ администратора": [
      "Invalid administrator key",
      "Әкімші кілті қате",
      "Administrator kaliti noto‘g‘ri",
    ],
    "Нужен ключ доступа администратора": [
      "Administrator access key required",
      "Әкімшінің қол жеткізу кілті қажет",
      "Administrator kirish kaliti kerak",
    ],
    "Слишком много попыток. Подождите минуту": [
      "Too many attempts. Wait a minute",
      "Әрекет саны тым көп. Бір минут күтіңіз",
      "Urinishlar soni juda ko‘p. Bir daqiqa kuting",
    ],
    "Очередь администратора недоступна": [
      "Administrator queue unavailable",
      "Әкімші кезегі қолжетімсіз",
      "Administrator navbati mavjud emas",
    ],
    "Очередь администратора заполнена": [
      "Administrator queue is full",
      "Әкімші кезегі толы",
      "Administrator navbati to‘lgan",
    ],
    "Проверка не найдена": [
      "Review not found",
      "Тексеру табылмады",
      "Tekshiruv topilmadi",
    ],
    "Обращение не найдено": [
      "Ticket not found",
      "Өтініш табылмады",
      "Murojaat topilmadi",
    ],
    "Обращение изменилось. Обновите данные и проверьте их заново": [
      "The ticket has changed. Refresh and review it again",
      "Өтініш өзгертілді. Деректерді жаңартып, қайта тексеріңіз",
      "Murojaat o‘zgartirilgan. Ma’lumotlarni yangilab, qayta tekshiring",
    ],
    "Обращение изменилось. Обновите данные перед удалением": [
      "The ticket has changed. Refresh it before deleting",
      "Өтініш өзгертілді. Жоймас бұрын деректерді жаңартыңыз",
      "Murojaat o‘zgartirilgan. O‘chirishdan oldin ma’lumotlarni yangilang",
    ],
    "Проверка уже завершена; черновик не изменён": [
      "The review is already complete; the draft was not changed",
      "Тексеру аяқталған; жоба өзгертілмеді",
      "Tekshiruv allaqachon tugatilgan; qoralama o‘zgartirilmagan",
    ],
    "Этот идентификатор уже связан с другим обращением": [
      "This identifier is already linked to another ticket",
      "Бұл идентификатор басқа өтінішке байланыстырылған",
      "Bu identifikator allaqachon boshqa murojaatga bog‘langan",
    ],
    "Не указана версия обращения": [
      "Ticket version not provided",
      "Өтініш нұсқасы көрсетілмеген",
      "Murojaat versiyasi ko‘rsatilmagan",
    ],
    "Неверный статус обращения": [
      "Invalid ticket status",
      "Өтініш күйі қате",
      "Murojaat holati noto‘g‘ri",
    ],
    "Добавьте текст ответа перед завершением проверки": [
      "Add a reply before completing the review",
      "Тексеруді аяқтамас бұрын жауап мәтінін енгізіңіз",
      "Tekshiruvni yakunlashdan oldin javob matnini qo‘shing",
    ],
    "Черновик должен быть строкой длиной не более 100000 символов": [
      "The draft must be text no longer than 100,000 characters",
      "Жоба ұзындығы 100 000 таңбадан аспайтын мәтін болуы керек",
      "Qoralama uzunligi 100000 belgidan oshmaydigan satr bo‘lishi kerak",
    ],
    "Текст обращения превышает допустимый размер": [
      "The ticket text exceeds the size limit",
      "Өтініш мәтіні рұқсат етілген көлемнен асады",
      "Murojaat matni ruxsat etilgan hajmdan oshdi",
    ],
    "Запрос слишком большой": [
      "Request is too large",
      "Сұрау тым үлкен",
      "So‘rov juda katta",
    ],
    "Автоматический разбор недоступен": [
      "Automatic analysis is unavailable",
      "Автоматты талдау қолжетімсіз",
      "Avtomatik tahlil mavjud emas",
    ],
    "Не удалось автоматически разобрать обращение": [
      "Could not analyze the ticket automatically",
      "Өтінішті автоматты түрде талдау мүмкін болмады",
      "Murojaatni avtomatik tahlil qilib bo‘lmadi",
    ],

    "РАЗБОР {id}": ["ANALYSIS {id}", "ТАЛДАУ {id}", "TAHLIL {id}"],
    "Обращение {id}: автоматический разбор не выполнен. Проверьте состояние передачи администратору.":
      [
        "Ticket {id}: automatic analysis was not completed. Check the handoff status.",
        "{id}-өтініш: автоматты талдау орындалмады. Әкімшіге жіберу күйін тексеріңіз.",
        "Murojaat {id}: avtomatik tahlil bajarilmadi. Administratorga yuborish holatini tekshiring.",
      ],
    "Оценка алгоритма: {value}% · не точность": [
      "Algorithm score: {value}% · not accuracy",
      "Алгоритм бағасы: {value}% · дәлдік көрсеткіші емес",
      "Algoritm bahosi: {value}% · aniqlik emas",
    ],
    "Разбор {id} готов. Категория: {category}. Приоритет: {priority}. {review}":
      [
        "Analysis {id} is ready. Category: {category}. Priority: {priority}. {review}",
        "{id}-талдау дайын. Санат: {category}. Басымдық: {priority}. {review}",
        "{id}-tahlil tayyor. Toifa: {category}. Ustuvorlik: {priority}. {review}",
      ],
    "Администратор подготовил ответ на обращение {id}.": [
      "The administrator prepared a reply to ticket {id}.",
      "Әкімші {id}-өтінішке жауап дайындады.",
      "Administrator {id}-murojaat uchun javob tayyorladi.",
    ],
    "ОБРАЩЕНИЕ #{id}": ["TICKET #{id}", "ӨТІНІШ #{id}", "MUROJAAT #{id}"],
    "{start}–{end} из {total}": [
      "{start}–{end} of {total}",
      "{start}–{end} / {total}",
      "{start}–{end} / {total}",
    ],
    "Сервер/регион: {value}.": [
      "Server/region: {value}.",
      "Сервер/аймақ: {value}.",
      "Server/hudud: {value}.",
    ],
    "Указанный ник: {value}.": [
      "Reported nickname: {value}.",
      "Көрсетілген ник: {value}.",
      "Ko‘rsatilgan nik: {value}.",
    ],
    "Указанные ссылки: {value}.": [
      "Reported references: {value}.",
      "Көрсетілген сілтемелер: {value}.",
      "Ko‘rsatilgan havolalar: {value}.",
    ],
    "Возможные пункты по указанному номеру": [
      "Possible clauses matching the reported number",
      "Көрсетілген нөмірге сәйкес ықтимал тармақтар",
      "Ko‘rsatilgan raqamga mos bo‘lishi mumkin bo‘lgan bandlar",
    ],
    "Это варианты для проверки, не подтверждённые цитаты. Одинаковые номера встречаются в разных разделах; проверьте смысл и доказательства.":
      [
        "These are candidates for review, not verified citations. Numbers can recur in different sections; check context and evidence.",
        "Бұлар — расталған дәйексөздер емес, тексерілетін нұсқалар. Бірдей нөмірлер әр бөлімде кездеседі; мағынасы мен дәлелдерді тексеріңіз.",
        "Bular tekshirish uchun variantlar, tasdiqlangan iqtiboslar emas. Bir xil raqamlar turli bo‘limlarda uchraydi; mazmun va dalillarni tekshiring.",
      ],
    "Пункты с указанными номерами не найдены.": [
      "No clauses with the reported numbers were found.",
      "Көрсетілген нөмірлері бар тармақтар табылмады.",
      "Ko‘rsatilgan raqamli bandlar topilmadi.",
    ],
    "Показаны не все варианты; проверьте остальные в исходном файле правил.": [
      "Not all candidates are shown; check the remaining ones in the original rules file.",
      "Барлық нұсқа көрсетілген жоқ; қалғанын бастапқы ережелер файлынан тексеріңіз.",
      "Barcha variantlar ko‘rsatilmagan; qolganlarini asl qoidalar faylida tekshiring.",
    ],
    "Найден ненумерованный термин из правил; он не заменяет проверенный номер пункта.":
      [
        "An unnumbered term was found in the rules; it does not replace a verified clause number.",
        "Ережелерден нөмірленбеген термин табылды; ол тексерілген тармақ нөмірін алмастырмайды.",
        "Qoidalardan raqamlanmagan atama topildi; u tekshirilgan band raqamini almashtirmaydi.",
      ],
    "Категория помощника: {value}.": [
      "Assistant category: {value}.",
      "Көмекші анықтаған санат: {value}.",
      "Yordamchi toifasi: {value}.",
    ],
    "Выгрузка подготовлена: {count}. Проверьте скачивание и храните файл приватно.":
      [
        "Export prepared: {count}. Check the download and keep the file private.",
        "Экспорт дайындалды: {count}. Жүктелгенін тексеріп, файлды құпия сақтаңыз.",
        "Yuklama tayyorlandi: {count}. Yuklab olinganini tekshiring va faylni maxfiy saqlang.",
      ],
  };

  const LANGUAGE_KEY = "support-copilot.interface-language";
  const languages = ["ru", "en", "kk", "uz"];
  const locales = { ru: "ru-RU", en: "en-US", kk: "kk-KZ", uz: "uz-UZ" };
  const messageIndex = { en: 0, kk: 1, uz: 2 };
  const originalText = new WeakMap();
  const originalAttributes = new WeakMap();
  const preserved = [
    "script",
    "style",
    "code",
    "pre",
    "textarea",
    "input",
    "option",
    "[data-i18n-preserve]",
    "#source-text",
    "#failure-source-text",
    "#review-message",
    "#operator-draft-text",
    "#review-context",
    "#citation-list",
    ".queue-item-copy strong",
    ".admin-item-message",
  ].join(",");
  const clean = (value) => value.replace(/\s+/g, " ").trim();
  let language = "ru";
  try {
    const stored = localStorage.getItem(LANGUAGE_KEY);
    if (languages.includes(stored)) language = stored;
  } catch (_) {
    // The selector remains usable for this page if storage is unavailable.
  }

  function t(source, values = {}) {
    if (typeof source !== "string") return String(source ?? "");
    const entry = Object.prototype.hasOwnProperty.call(messages, source)
      ? messages[source]
      : null;
    const translated =
      language === "ru" || !entry
        ? source
        : entry[messageIndex[language]] || source;
    return translated.replace(/\{(\w+)\}/g, (match, key) =>
      Object.prototype.hasOwnProperty.call(values, key)
        ? String(values[key])
        : match,
    );
  }

  function translateText(node) {
    const parent = node.parentElement;
    if (!parent || parent.closest(preserved)) return;
    let entry = originalText.get(node);
    if (!entry || node.data !== entry.rendered) {
      const source = clean(node.data);
      if (!Object.prototype.hasOwnProperty.call(messages, source)) {
        originalText.delete(node);
        return;
      }
      entry = { source, raw: node.data, rendered: node.data };
    }
    const leading = entry.raw.match(/^\s*/)[0];
    const trailing = entry.raw.match(/\s*$/)[0];
    const rendered =
      language === "ru" ? entry.raw : `${leading}${t(entry.source)}${trailing}`;
    entry.rendered = rendered;
    originalText.set(node, entry);
    if (node.data !== rendered) node.data = rendered;
  }

  function translateAttributes(element) {
    const attributes = originalAttributes.get(element) || {};
    for (const name of ["aria-label", "placeholder", "title"]) {
      const value = element.getAttribute(name);
      if (value === null) continue;
      let entry = attributes[name];
      if (!entry || value !== entry.rendered) {
        const source = clean(value);
        if (!Object.prototype.hasOwnProperty.call(messages, source)) {
          delete attributes[name];
          continue;
        }
        entry = { source, raw: value, rendered: value };
      }
      const rendered = language === "ru" ? entry.raw : t(entry.source);
      entry.rendered = rendered;
      attributes[name] = entry;
      if (value !== rendered) element.setAttribute(name, rendered);
    }
    originalAttributes.set(element, attributes);
  }

  function scan(root) {
    if (root.nodeType === Node.TEXT_NODE) {
      translateText(root);
      return;
    }
    if (
      root.nodeType !== Node.ELEMENT_NODE &&
      root.nodeType !== Node.DOCUMENT_NODE
    )
      return;
    if (root.nodeType === Node.ELEMENT_NODE) translateAttributes(root);
    const walker = document.createTreeWalker(
      root,
      NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT,
    );
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (node.nodeType === Node.TEXT_NODE) translateText(node);
      else translateAttributes(node);
    }
  }

  function applyLanguage(next, persist = true) {
    if (!languages.includes(next)) return;
    language = next;
    document.documentElement.lang = language;
    const selector = document.getElementById("language-switch");
    if (selector) selector.value = language;
    if (persist) {
      try {
        localStorage.setItem(LANGUAGE_KEY, language);
      } catch (_) {
        /* unavailable */
      }
    }
    scan(document);
    document.dispatchEvent(
      new CustomEvent("copilot:languagechange", { detail: { language } }),
    );
  }

  window.CopilotI18n = Object.freeze({
    t,
    get language() {
      return language;
    },
    get locale() {
      return locales[language];
    },
    setLanguage: applyLanguage,
  });
  applyLanguage(language, false);
  document
    .getElementById("language-switch")
    ?.addEventListener("change", (event) => applyLanguage(event.target.value));
  window.addEventListener("storage", (event) => {
    if (event.key === LANGUAGE_KEY && languages.includes(event.newValue))
      applyLanguage(event.newValue, false);
  });
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type === "characterData") translateText(mutation.target);
      else if (mutation.type === "attributes")
        translateAttributes(mutation.target);
      else for (const node of mutation.addedNodes) scan(node);
    }
  });
  observer.observe(document.documentElement, {
    subtree: true,
    childList: true,
    characterData: true,
    attributes: true,
    attributeFilter: ["aria-label", "placeholder", "title"],
  });
})();
