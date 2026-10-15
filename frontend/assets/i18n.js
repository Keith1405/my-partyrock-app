// Translate interface copy only. Never rewrite entered medicine names or doses.
(() => {
  const copy = [
    ["Type medicine details or upload a clear label photo. Show the name, strength and instructions. You may cover personal details.", "Taip butiran ubat atau muat naik foto label yang jelas. Pastikan nama, kekuatan dan arahan kelihatan. Anda boleh menutup maklumat peribadi.", "输入药物详情或上传清晰的标签照片。请显示名称、规格和用药说明。可以遮盖个人资料。"],
    ["Add other medicines and allergies, if known. Blank means not provided. Generate key precautions and pharmacist questions.", "Masukkan ubat lain dan alahan, jika diketahui. Ruang kosong bermaksud belum diberikan. Jana langkah berjaga-jaga dan soalan untuk ahli farmasi.", "如知道，请填写其他药物和过敏信息。留空表示未提供。生成注意事项和药剂师问题。"],
    ["Ask about your medicines or precautions.", "Tanya tentang ubat atau langkah berjaga-jaga.", "询问药物或注意事项。"],
    ["— a summary to share with your pharmacist.", "— ringkasan untuk dikongsi dengan ahli farmasi.", "— 可分享给药剂师的摘要。"],
    ["Have unwanted medicines, vitamins or supplements?", "Ada ubat, vitamin atau suplemen yang tidak diperlukan?", "有不需要的药物、维生素或补充剂？"],
    ["Add their details and your town or postcode to find a listed collection point. Call to confirm acceptance.", "Masukkan butirannya serta bandar atau poskod untuk mencari pusat pengumpulan yang disenaraikan. Telefon untuk mengesahkan penerimaan.", "填写详情及城市或邮政编码，查找列出的回收点。请致电确认是否接受。"],

    ['SmartMed Cycle — Know your medicine', 'SmartMed Cycle — Kenali ubat anda', 'SmartMed Cycle — 了解您的药物'],
    ['Skip to medicine details', 'Langkau ke butiran ubat', '跳至药物详情'],
    ['Main navigation', 'Navigasi utama', '主导航'],
    ['SmartMed Cycle logo', 'Logo SmartMed Cycle', 'SmartMed Cycle 标志'],
    ['Medicine', 'Ubat', '药物'],
    ['Precautions', 'Langkah berjaga-jaga', '注意事项'],
    ['Ask', 'Tanya', '提问'],
    ['Returns', 'Pemulangan', '退回药物'],
    ['Preferred language', 'Bahasa pilihan', '首选语言'],
    ['Open navigation', 'Buka navigasi', '打开导航'],
    ['Close navigation', 'Tutup navigasi', '关闭导航'],
    ['Know your medicine.', 'Kenali ubat anda.', '了解您的药物。'],
    ['Feel prepared.', 'Bersedia dengan yakin.', '做好准备。'],
    ['Turn your medicine label into clear information', 'Fahami maklumat pada label ubat anda', '将药物标签转化为清晰的信息'],
    ['and questions for your pharmacist.', 'dan sediakan soalan untuk ahli farmasi anda.', '并准备向药剂师提出的问题。'],
    ['Start with my medicine', 'Mulakan dengan ubat saya', '从我的药物开始'],
    ['Preparation tool only. Always check your original label and speak with your pharmacist.', 'Alat persediaan sahaja. Sentiasa semak label asal dan berbincang dengan ahli farmasi anda.', '本工具仅供准备参考。请始终核对原始标签并咨询药剂师。'],
    ['Medicine details', 'Butiran ubat', '药物详情'],
    ['Medicine name and details', 'Nama dan butiran ubat', '药物名称和详情'],
    ['Medicine name, strength and label instructions', 'Nama ubat, kekuatan dan arahan pada label', '药物名称、规格及标签说明'],
    ['Photo upload', 'Muat naik foto', '上传照片'],
    ['Upload label photo', 'Muat naik foto label', '上传标签照片'],
    ['JPG, PNG or WebP', 'JPG, PNG atau WebP', 'JPG、PNG 或 WebP'],
    ['✕ Remove photo', '✕ Buang foto', '✕ 移除照片'],
    ['Extract from Photo', 'Ekstrak daripada foto', '从照片提取'],
    ['Extract label', 'Ekstrak label', '提取标签'],
    ['Upload a label photo, then choose Extract label.', 'Muat naik foto label, kemudian pilih Ekstrak label.', '上传标签照片，然后选择“提取标签”。'],
    ['How it works', 'Cara penggunaan', '使用步骤'],
    ['Add your medicine', 'Masukkan ubat anda', '添加您的药物'],
    ['Type it or upload a photo', 'Taip butiran atau muat naik foto', '输入详情或上传照片'],
    ['of your label.', 'label ubat anda.', '显示您的药物标签。'],
    ['Get clear information', 'Dapatkan maklumat yang jelas', '获取清晰信息'],
    ['See key points in plain language.', 'Lihat perkara penting dalam bahasa yang mudah.', '用简单语言查看要点。'],
    ['Take to your pharmacist', 'Bawa kepada ahli farmasi', '带给您的药剂师'],
    ['Bring your questions and', 'Bawa soalan anda dan', '带上您的问题并'],
    ['feel prepared.', 'bersedia dengan yakin.', '做好准备。'],
    ['01 / UNDERSTAND', '01 / FAHAMI', '01 / 了解'],
    ['Your medicine, in plain language.', 'Ubat anda, dalam bahasa yang mudah.', '用简单语言了解您的药物。'],
    ['Type medicine details or upload a readable label photo — either is enough. If you use both, the Medicine Card compares them and flags conflicts. The medicine name, strength, and instructions must be readable. Cover personal details if you wish.', 'Taip butiran ubat atau muat naik foto label yang boleh dibaca — salah satu sudah memadai. Jika anda menggunakan kedua-duanya, Kad Ubat akan membandingkan maklumat dan menandakan percanggahan. Nama ubat, kekuatan dan arahan mestilah boleh dibaca. Anda boleh menutup butiran peribadi jika mahu.', '输入药物详情或上传清晰可读的标签照片，任选其一即可。如果同时提供，药物卡会比较两者并提示冲突。药物名称、规格和说明必须清晰可读。您可以遮盖个人信息。'],
    ['Always compare the Medicine Card with your original label before continuing to precautions.', 'Sentiasa bandingkan Kad Ubat dengan label asal sebelum meneruskan ke langkah berjaga-jaga.', '继续查看注意事项前，请始终将药物卡与原始标签核对。'],
    ['Medicine Card', 'Kad Ubat', '药物卡'],
    ['Generate', 'Jana', '生成'],
    ['Your medicine card will appear here.', 'Kad ubat anda akan dipaparkan di sini.', '您的药物卡将显示在这里。'],
    ['02 / Check my precautions', '02 / Semak langkah berjaga-jaga saya', '02 / 查看我的注意事项'],
    ['Add other medicines and allergy history below, if known. Blank means not provided — it does not mean none. Generate this section to get a list of points to discuss with your pharmacist.', 'Masukkan ubat lain dan sejarah alahan di bawah, jika diketahui. Ruang kosong bermaksud maklumat tidak diberikan — bukan tiada. Jana bahagian ini untuk mendapatkan senarai perkara yang boleh dibincangkan dengan ahli farmasi anda.', '如果知道，请在下方填写其他药物和过敏史。留空表示未提供信息，并不代表没有。生成此部分，以获取可与药剂师讨论的要点。'],
    ['If you updated Section 1, regenerate the Medicine Card first, then regenerate this section.', 'Jika anda mengemas kini Bahagian 1, jana semula Kad Ubat dahulu, kemudian jana semula bahagian ini.', '如果更新了第 1 部分，请先重新生成药物卡，再重新生成此部分。'],
    ['Other Medicines and Supplements', 'Ubat lain dan suplemen', '其他药物和补充剂'],
    ['Optional', 'Pilihan', '选填'],
    ['Other medicines you are currently taking. Add names and doses if known. Example: Atorvastatin 20 mg once daily; Aspirin 100 mg once daily.', 'Ubat lain yang sedang anda ambil.\nMasukkan nama dan dos jika diketahui.\n\nContoh: Atorvastatin 20 mg sekali sehari; Aspirin 100 mg sekali sehari.', '您目前服用的其他药物。\n如知道，请填写名称和剂量。\n\n例如：阿托伐他汀 20 mg，每日一次；阿司匹林 100 mg，每日一次。'],
    ['Medicine Allergies and Reactions', 'Alahan ubat dan tindak balas', '药物过敏和反应'],
    ["Any known medicine or food allergies, and what reaction happened. Example: Penicillin — rash and swelling. Write 'None known' or 'Not sure' if applicable. Also note any supplements or herbal products you take.", "Alahan ubat atau makanan yang diketahui dan tindak balas yang berlaku.\n\nContoh: Penisilin — ruam dan bengkak. Tulis 'Tiada yang diketahui' atau 'Tidak pasti' jika berkenaan.\nNyatakan juga suplemen atau produk herba yang anda ambil.", '任何已知药物或食物过敏，以及发生的反应。\n\n例如：青霉素 — 皮疹和肿胀。如适用，请填写“无已知过敏”或“不确定”。\n也请注明服用的补充剂或草药产品。'],
    ['My Medicine Summary', 'Ringkasan ubat saya', '我的药物摘要'],
    ['Run', 'Jalankan', '运行'],
    ["You're all set to Run", 'Sedia untuk dijalankan', '已准备好运行'],
    ['03 / Ask about my medicines', '03 / Tanya tentang ubat saya', '03 / 询问我的药物'],
    ['Ask anything about your medicine, precautions, or what to tell your pharmacist.', 'Tanya tentang ubat anda, langkah berjaga-jaga atau perkara yang perlu diberitahu kepada ahli farmasi.', '询问药物、注意事项或应向药剂师说明的内容。'],
    ['Try:', 'Cuba:', '试试：'],
    ['"Prepare my pharmacist summary"', '"Sediakan ringkasan untuk ahli farmasi saya"', '“准备给药剂师的摘要”'],
    ['— get a ready-to-share summary with your medicine details, uncertainties, and questions to ask.', '— dapatkan ringkasan yang sedia dikongsi, termasuk butiran ubat, perkara yang tidak pasti dan soalan anda.', '— 获取可分享的摘要，包含药物详情、不确定事项和要问的问题。'],
    ['Medical emergency?', 'Kecemasan perubatan?', '医疗紧急情况？'],
    ['In Malaysia, call', 'Di Malaysia, hubungi', '在马来西亚，请立即拨打'],
    ['now. Outside Malaysia, call your local emergency number. Do not wait for this tool.', 'sekarang. Di luar Malaysia, hubungi nombor kecemasan tempatan. Jangan tunggu alat ini.', '。在马来西亚以外，请拨打当地急救电话。不要等待本工具。'],
    ['SmartMed Help', 'Bantuan SmartMed', 'SmartMed 帮助'],
    ['Ask anything. For example: explain this instruction, prepare my pharmacist summary, quiz me', 'Tanya apa-apa. Contoh: terangkan arahan ini, sediakan ringkasan untuk ahli farmasi saya, uji pengetahuan saya', '提出问题。例如：解释这条说明、准备给药剂师的摘要、考考我'],
    ['Send', 'Hantar', '发送'],
    ['04 / Return unused medicines', '04 / Pulangkan ubat yang tidak digunakan', '04 / 退回未使用的药物'],
    ['You can return', 'Anda boleh memulangkan', '您可以退回'],
    ['any', 'apa-apa', '任何'],
    ['unwanted medicine — prescription medicines, over-the-counter products, vitamins, supplements, or medicines found at home.', 'ubat yang tidak diperlukan — ubat preskripsi, ubat tanpa preskripsi, vitamin, suplemen atau ubat yang dijumpai di rumah.', '不需要的药物 — 处方药、非处方药、维生素、补充剂或家中找到的药物。'],
    ["Enter the medicine details and your location below and we'll help you find a verified drop-off point near you!", 'Masukkan butiran ubat dan lokasi anda di bawah untuk membantu kami mencari pusat pemulangan yang disahkan berhampiran anda!', '在下方填写药物详情和位置，我们将帮助您寻找附近经过核实的回收点！'],
    ['Not sure if you should stop taking a medicine?', 'Tidak pasti sama ada perlu berhenti mengambil ubat?', '不确定是否应停止服药？'],
    ['Check with your pharmacist or prescriber', 'Semak dengan ahli farmasi atau pemberi preskripsi anda', '请咨询药剂师或开药的医务人员'],
    ['before', 'sebelum', '在'],
    ['returning it.', 'memulangkannya.', '退回药物之前。'],
    ['Official return directory:', 'Direktori pemulangan rasmi:', '官方回收目录：'],
    ['— search by state, city, or postcode.', '— cari mengikut negeri, bandar atau poskod.', '— 按州、城市或邮政编码搜索。'],
    ['Your Location', 'Lokasi anda', '您的位置'],
    ['Enter your area, city, or postcode (e.g. 50480 Kuala Lumpur, Petaling Jaya, Johor Bahru) — use the official locator to check participating centres.', 'Masukkan kawasan, bandar atau poskod anda (contoh: 50480 Kuala Lumpur, Petaling Jaya, Johor Bahru) — gunakan pencari lokasi rasmi untuk menyemak pusat yang mengambil bahagian.', '输入地区、城市或邮政编码（例如：50480 Kuala Lumpur、Petaling Jaya、Johor Bahru），请使用官方定位工具查看参与的回收中心。'],
    ['Return Item Details', 'Butiran ubat untuk dipulangkan', '退回药物详情'],
    ['Medicine name and form (e.g. Paracetamol 500 mg tablets) Prescription or over-the-counter (if known) Quantity remaining (e.g. 14 tablets — leave blank if unsure) Item type if special: liquid / inhaler / cream / drops / needles or sharps Reason: expired / no longer needed / course completed / found at home / unsure', 'Nama dan bentuk ubat (contoh: tablet Paracetamol 500 mg)\nUbat preskripsi atau tanpa preskripsi (jika diketahui)\nBaki kuantiti (contoh: 14 tablet — biarkan kosong jika tidak pasti)\nJenis khas: cecair / inhaler / krim / titisan / jarum atau benda tajam\nSebab: tamat tempoh / tidak diperlukan lagi / rawatan selesai / dijumpai di rumah / tidak pasti', '药物名称和剂型（例如：Paracetamol 500 mg 片剂）\n处方药或非处方药（如知道）\n剩余数量（例如：14 片 — 不确定请留空）\n特殊类型：液体 / 吸入器 / 乳膏 / 滴剂 / 针头或锐器\n原因：过期 / 不再需要 / 疗程结束 / 家中找到 / 不确定'],
    ['Return Item Photo', 'Foto ubat untuk dipulangkan', '退回药物照片'],
    ['Optional. Upload a clear photo of the labelled packaging. The label must be visible and readable. Unlabelled pills with no readable label will not be identified from appearance.', 'Pilihan. Muat naik foto pembungkusan berlabel yang jelas.\nLabel mestilah kelihatan dan boleh dibaca.\nPil tanpa label yang boleh dibaca tidak akan dikenal pasti berdasarkan rupa.', '选填。上传带标签包装的清晰照片。\n标签必须可见且清晰可读。\n没有可读标签的药片不会仅凭外观进行识别。'],
    ['My Return Plan', 'Pelan pemulangan saya', '我的退回计划'],
    ['Generating…', 'Sedang menjana…', '正在生成…'],
    ['No response.', 'Tiada respons.', '无响应。'],
    ['Request failed', 'Permintaan gagal', '请求失败'],
    ['This local preview is not connected to the medicine service. The deployed app will generate your results here.', 'Pratonton tempatan ini tidak disambungkan kepada perkhidmatan ubat. Aplikasi yang diterbitkan akan menjana keputusan anda di sini.', '此本地预览未连接药物服务。部署后的应用将在这里生成结果。'],
    ['This local preview is not connected to SmartMed Help. Chat is available in the deployed app.', 'Pratonton tempatan ini tidak disambungkan kepada Bantuan SmartMed. Sembang tersedia dalam aplikasi yang diterbitkan.', '此本地预览未连接 SmartMed 帮助。聊天功能在部署后的应用中可用。'],
    ['Language changed. Regenerate existing results for this language; earlier responses keep their original wording.', 'Bahasa telah ditukar. Jana semula keputusan sedia ada dalam bahasa ini; respons terdahulu kekal dalam bahasa asal.', '语言已更改。请重新生成结果以使用此语言；先前的回复保留原文。'],
    ["Hi! 👋 I'm SmartMed Help. Ask me anything about your medicine.\n\nTry:\n- 💬 Explain this instruction simply\n- ⏰ What if I miss a dose?\n- 📋 Prepare my pharmacist summary\n- 🧠 Quiz me on my medicine\n\n🚨 Medical emergency? Call 999 (Malaysia) or your local emergency number now.", 'Hai! 👋 Saya Bantuan SmartMed. Tanya apa-apa tentang ubat anda.\n\nCuba:\n- 💬 Terangkan arahan ini dengan mudah\n- ⏰ Bagaimana jika saya terlepas satu dos?\n- 📋 Sediakan ringkasan untuk ahli farmasi saya\n- 🧠 Uji pengetahuan saya tentang ubat\n\n🚨 Kecemasan perubatan? Hubungi 999 (Malaysia) atau nombor kecemasan tempatan sekarang.', '您好！👋 我是 SmartMed 帮助。您可以询问任何药物相关问题。\n\n试试：\n- 💬 用简单语言解释这条说明\n- ⏰ 如果漏服一次怎么办？\n- 📋 准备给药剂师的摘要\n- 🧠 测试我的药物知识\n\n🚨 医疗紧急情况？请立即拨打 999（马来西亚）或当地急救电话。'],
    ['Disposal Guide: What Can & Cannot Be Returned', 'Panduan Pelupusan: Apa Boleh & Tidak Boleh Dikembalikan', '药物处置指南：哪些可以回收与不可回收'],
    ['Click to expand', 'Klik untuk buka', '点击展开'],
    ['Click to collapse', 'Klik untuk tutup', '点击折叠'],
    ['What can be disposed of in collection bins?', 'Apa yang boleh dilupuskan dalam tong pengumpulan?', '哪些药物可以投入回收箱？'],
    ['The following medicines are safely accepted at all participating collection boxes:', 'Ubat-ubatan berikut diterima dengan selamat di semua tong pengumpulan yang mengambil bahagian:', '以下药物均可在所有参与计划的回收箱安全处置：'],
    ['Tablets', 'Tablet', '药片'],
    ['Oral pills', 'Pil telan', '口服药丸'],
    ['Capsules', 'Kapsul', '胶囊'],
    ['Hard & softgel', 'Kapsul keras & lembut', '硬胶囊与软胶囊'],
    ['Inhalers', 'Ubat sedut (Inhaler)', '吸入器'],
    ['Puffers, disks', 'Alat sedut puf & diskus', '气雾吸入剂与吸入盘'],
    ['Liquid Meds', 'Ubat cecair', '液体药物'],
    ['Syrups (tightly sealed)', 'Sirap (penutup ketat)', '口服糖浆（密封良好）'],
    ['Eye Drops', 'Titis mata', '滴眼液'],
    ['Bottles / ampoules', 'Botol / ampul cecair', '药瓶与安瓿'],
    ['Nasal Sprays', 'Semburan hidung', '鼻喷剂'],
    ['Nasal pumps', 'Pam semburan hidung', '鼻腔喷雾泵'],
    ['Suppositories', 'Ubat supositori', '栓剂'],
    ['& Pessaries', '& pesari wanita', '及阴道栓剂'],
    ['Insulin Pens', 'Pen suntikan insulin', '胰岛素注射笔'],
    ['Pens & cartridges', 'Pen & kartrij ubat', '药笔及笔芯'],
    ['Patches', 'Pelekat ubat', '药膏贴片'],
    ['Transdermal patches', 'Pelekat telap kulit', '透皮贴剂'],
    ['Sachets', 'Paket serbuk', '袋装冲剂'],
    ['Powders & ORS', 'Serbuk garam ORS', '药粉与口服补液盐'],
    ['Topical Preparations', 'Persediaan ubat sapu', '外用制剂'],
    ['Creams, gels & ointments', 'Krim, gel & salap', '乳膏、凝胶与软膏'],
    ['What cannot be disposed?', 'Apa yang TIDAK boleh dilupuskan?', '哪些物品不可投入回收箱？'],
    ['Do not drop these into collection boxes:', 'Jangan masukkan bahan ini ke dalam tong pengumpulan:', '请勿将以下物品投入药物回收箱：'],
    ['Sharp Materials', 'Bahan tajam berbahaya', '锐利尖锐物品'],
    ['Needles & lancets (Use sharps bin)', 'Jarum & lanset (Guna tong khas sisa tajam)', '针头与采血针（请使用利器盒）'],
    ['Medical Devices', 'Peranti perubatan', '医疗器械'],
    ['Glucometers & BP meters', 'Alat ujian gula darah & tekanan darah', '血糖仪与血压计'],
    ['Clinical Wastes', 'Bahan sisa klinikal', '临床医疗废物'],
    ['Used gauze, diapers, IV sets', 'Kain kasa terpakai, lampin, tiub IV', '用过的纱布、尿布、输液管'],
    ['Prosthetics', 'Alat anggota palsu', '义肢与矫形器'],
    ['Artificial limbs & braces', 'Tangan/kaki palsu & pendakap', '假肢与支撑支具'],
    ['Environmental Note:', 'Nota Alam Sekitar:', '环保提示：'],
    ['Never flush medicines down the toilet or throw them into household trash.', 'Jangan sesekali pam ubat ke dalam tandas atau buang ke dalam tong sampah rumah.', '切勿将药物冲入马桶或随生活垃圾丢弃。'],
    ['The request could not finish. Check your connection and try again.', 'Permintaan tidak dapat diselesaikan. Semak sambungan anda dan cuba lagi.', '请求未能完成。请检查网络连接并重试。'],
    ['Your label details will appear here.', 'Butiran label anda akan dipaparkan di sini.', '标签详情将显示在这里。'],
    ['Did anything look incorrect or unclear?', 'Ada maklumat yang kelihatan salah atau tidak jelas?', '是否有任何信息不正确或不清晰？'],
    ['🚩 Report issue', '🚩 Laporkan isu', '🚩 反馈问题'],
    ['Report issue', 'Laporkan isu', '反馈问题'],
    ['Report an issue with this output', 'Laporkan isu berkaitan maklumat ini', '反馈此输出的问题'],
    ['Flag AI Output', 'Laporkan Output AI', '反馈 AI 输出'],
    ['What seems incorrect or concerning?', 'Apakah yang kelihatan salah atau meragukan?', '您觉得哪项内容存在错误或令人担忧？'],
    ['Incorrect dose, frequency, or instructions', 'Dos, kekerapan atau arahan salah', '剂量、频次或用药说明错误'],
    ['Missing safety warning or interaction', 'Amaran keselamatan atau interaksi ubat tiada', '缺少重要的安全警告或药物相互作用'],
    ['Unclear, confusing, or contradictory wording', 'Ayat mengelirukan atau bercanggah', '用词晦涩、易混淆或前后矛盾'],
    ['Wrong medicine or active ingredient', 'Nama ubat atau bahan aktif salah', '药物名称或活性成分错误'],
    ['Other safety concern', 'Kebimbangan keselamatan lain', '其他安全顾虑'],
    ['Details (optional):', 'Butiran (pilihan):', '详情（选填）：'],
    ['Describe what looks wrong or what you expected...', 'Terangkan apa yang kelihatan salah atau apa yang anda jangkakan...', '请描述错误之处或您的预期...'],
    ['Cancel', 'Batal', '取消'],
    ['Submit Report', 'Hantar Laporan', '提交反馈'],
    ['Thank you! Your feedback was logged to improve our clinical prompts.', 'Terima kasih! Maklum balas anda telah direkodkan untuk menambah baik ketepatan klinikal.', '感谢您！您的反馈已记录，用于改进临床提示词。'],
    ['✅ Thank you! Your feedback was logged to improve our clinical prompts.', '✅ Terima kasih! Maklum balas anda telah direkodkan untuk menambah baik ketepatan klinikal.', '✅ 感谢您！您的反馈已记录，用于改进临床提示词。'],
    ['Section', 'Bahagian', '部分'],
    ['📋 Clinical Triage & Feedback Log', '📋 Log Triaj Klinikal & Maklum Balas', '📋 临床分流与反馈日志'],
    ['Clinical Triage Log', 'Log Triaj Klinikal', '临床分流日志'],
    ['User-flagged AI outputs for prompt engineering and clinical review.', 'Output AI yang ditandakan pengguna untuk semakan klinikal dan kejuruteraan prompt.', '用户标记的 AI 输出，用于提示词工程与临床审核。'],
    ['No issues flagged yet.', 'Tiada isu ditandakan lagi.', '暂无标记的问题。'],
    ['When users flag an output with 🚩 Report issue, submissions appear here for clinical triage.', 'Apabila pengguna menandakan maklumat dengan 🚩 Laporkan isu, laporan akan dipaparkan di sini untuk triaj klinikal.', '当用户点击“🚩 反馈问题”时，提交的报告将显示在此处以供临床分流。'],
    ['Reason', 'Sebab', '原因'],
    ['📥 Download JSON', '📥 Muat Turun JSON', '📥 下载 JSON'],
    ['Clear Log', 'Kosongkan Log', '清除日志'],
    ['Close', 'Tutup', '关闭'],
    ['Refresh', 'Muat Semula', '刷新'],
    ['(No extra notes provided)', '(Tiada butiran tambahan diberikan)', '(未提供额外说明)'],
    ['Clear all logged feedback reports?', 'Kosongkan semua laporan maklum balas yang direkodkan?', '清除所有已记录的反馈报告？'],
  ];
  const normalize = text => text.replace(/\s+/g, ' ').trim();
  const translations = new Map(copy.map(row => [normalize(row[0]), row]));
  const languages = { English: { index: 0, tag: 'en' }, 'Bahasa Melayu': { index: 1, tag: 'ms' }, '中文': { index: 2, tag: 'zh-Hans' } };
  let language = 'English';
  const t = source => translations.get(normalize(source))?.[languages[language].index] ?? source;
  const bindings = [];
  const attributes = [];

  function collectBindings() {
    bindings.length = 0;
    attributes.length = 0;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (node.parentElement && node.parentElement.closest('script, style, #preferred_language')) continue;
      const source = node.nodeValue;
      if (translations.has(normalize(source))) bindings.push({ node, source });
    }
    document.querySelectorAll('[placeholder], [aria-label], [alt]').forEach(el => {
      for (const name of ['placeholder', 'aria-label', 'alt']) {
        const source = el.getAttribute(name);
        if (source && translations.has(normalize(source))) attributes.push({ el, name, source });
      }
    });
  }

  const title = document.title;
  const select = document.getElementById('preferred_language');
  const notice = document.createElement('p');
  notice.className = 'notice language-notice';
  notice.setAttribute('role', 'status');
  notice.hidden = true;
  document.querySelector('.topbar').after(notice);
  function apply(value, announce = false) {
    language = Object.hasOwn(languages, value) ? value : 'English';
    select.value = language;
    document.documentElement.lang = languages[language].tag;
    document.title = t(title);
    collectBindings();
    for (const { node, source } of bindings) {
      if (node.isConnected) node.nodeValue = source.match(/^\s*/)[0] + t(source) + source.match(/\s*$/)[0];
    }
    for (const { el, name, source } of attributes) el.setAttribute(name, t(source));
    document.querySelectorAll('[data-ui-copy]').forEach(el => { el.textContent = t(el.dataset.uiCopy); });
    const menu = document.getElementById('menu_toggle');
    if (menu) menu.setAttribute('aria-label', t(menu.getAttribute('aria-expanded') === 'true' ? 'Close navigation' : 'Open navigation'));
    if (announce) notice.hidden = false;
    notice.textContent = t('Language changed. Regenerate existing results for this language; earlier responses keep their original wording.');
    try { localStorage.setItem('smartmed.language', language); } catch { /* Storage may be unavailable. */ }
  }
  window.SmartMedI18n = { t, apply };
  let saved;
  try { saved = localStorage.getItem('smartmed.language'); } catch { /* Use English. */ }
  apply(saved || select.value);
  select.addEventListener('change', () => apply(select.value, true));
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => apply(language));
  }
})();
