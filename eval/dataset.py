LABELED_QUESTIONS = [
 
    # PLATÃO
    {
        "question": "O que é a Alegoria da Caverna em A República de Platão?",
        "book_title": "The Republic",
        "ground_truth": (
            "Na Alegoria da Caverna (República, Livro VII), Platão descreve prisioneiros "
            "acorrentados numa caverna que veem apenas sombras projetadas na parede e "
            "tomam essas sombras pela realidade. Quando um deles é libertado e vê o sol "
            "(símbolo do Bem e do conhecimento verdadeiro), tem dificuldade em aceitar "
            "a nova realidade. A alegoria ilustra a distinção entre o mundo sensível "
            "(opiniões, aparências) e o mundo inteligível (Forms/Ideias), e fundamenta "
            "a missão do filósofo-rei de conduzir os demais ao conhecimento verdadeiro."
        ),
        "student_level": "superior",
        "subset": "qa",
        "gutenberg_id": 1497,
    },
    {
        "question": "Como Sócrates defende sua vida filosófica na Apologia de Platão?",
        "book_title": "Apology",
        "ground_truth": (
            "Na Apologia, Sócrates defende-se das acusações de impiedade e corrupção da "
            "juventude argumentando que sua missão filosófica foi ordenada pelo deus de "
            "Delfos: ao constatar que ninguém era realmente sábio, tornou-se um 'moscardo' "
            "que desperta Atenas para o exame racional da vida. Declara que prefere morrer "
            "a abandonar a filosofia, afirmando que a vida não examinada não vale a pena "
            "ser vivida. Recusa tanto a fuga quanto o silêncio como alternativas à morte."
        ),
        "student_level": "superior",
        "subset": "qa",
        "gutenberg_id": 1656,
    },
    {
        "question": "Qual é o argumento central do Fédon sobre a imortalidade da alma?",
        "book_title": "Phaedo",
        "ground_truth": (
            "No Fédon, Platão apresenta quatro argumentos principais para a imortalidade "
            "da alma: (1) o Argumento dos Contrários — opostos se geram mutuamente, então "
            "vida e morte se alternam; (2) a Reminiscência — conhecer é recordar, logo a "
            "alma existia antes do nascimento; (3) a Afinidade — a alma é simples e "
            "imutável como as Formas, portanto não pode se dissolver; (4) a Forma da Vida "
            "— a alma participa essencialmente da Forma Vida e não pode admitir a morte. "
            "O diálogo ocorre na cela de Sócrates no dia de sua execução."
        ),
        "student_level": "superior",
        "subset": "qa",
        "gutenberg_id": 1658,
    },
    {
        "question": "O que Sócrates entende por Eros no Banquete de Platão?",
        "book_title": "Symposium",
        "ground_truth": (
            "No Banquete (Symposium), o discurso de Sócrates, atribuído à sacerdotisa "
            "Diotima, apresenta Eros não como um deus, mas como um daemon intermediário "
            "entre mortais e imortais. Eros é filho de Poros (recurso) e Penia (pobreza), "
            "sendo sempre desejante e nunca plenamente saciado. A Escada de Diotima "
            "descreve a ascensão do amor: do belo corpo individual a belos corpos em geral, "
            "belas almas, belas atividades, belo conhecimento e, por fim, a Beleza em si "
            "mesma (a Forma do Belo). Eros é, portanto, o impulso filosófico rumo ao Bem."
        ),
        "student_level": "superior",
        "subset": "qa",
        "gutenberg_id": 1600,
    },
 
    # ARISTÓTELES
    {
        "question": "O que é eudaimonia para Aristóteles na Ética a Nicômaco?",
        "book_title": "Nicomachean Ethics",
        "ground_truth": (
            "Na Ética a Nicômaco, Aristóteles define eudaimonia (felicidade ou florescimento "
            "humano) como o bem supremo e o fim último da vida humana. Ela não é um estado "
            "passivo de prazer, mas uma atividade da alma em conformidade com a virtude "
            "(arete). O homem feliz exerce a função própria do ser humano — a atividade "
            "racional — com excelência ao longo de uma vida completa. Virtudes como "
            "coragem, temperança e justiça são hábitos adquiridos pela prática, constituindo "
            "o meio-termo entre extremos (doutrina do justo meio)."
        ),
        "student_level": "superior",
        "subset": "qa",
        "gutenberg_id": 8438,
    },
    {
        "question": "Como Aristóteles define o ser humano como animal político na Política?",
        "book_title": "Politics",
        "ground_truth": (
            "Na Política, Aristóteles afirma que o homem é por natureza um animal político "
            "(zoon politikon), pois somente na polis pode realizar plenamente sua natureza "
            "racional e moral. A polis não é uma convenção artificial, mas o telos natural "
            "da evolução social: família, aldeia, cidade-estado. Quem vive fora da "
            "comunidade política é, segundo Aristóteles, uma besta ou um deus. A polis "
            "existe para o bem viver (eu zen), não apenas para a sobrevivência (zen)."
        ),
        "student_level": "superior",
        "subset": "qa",
        "gutenberg_id": 6762,
    },
 
    # AGOSTINHO
    {
        "question": "Qual é o papel da memória nas Confissões de Agostinho?",
        "book_title": "Confessions",
        "ground_truth": (
            "Nas Confissões (Livro X), Agostinho explora a memória como o ventre da mente, "
            "um vasto palácio interior onde se armazenam imagens, experiências e até a "
            "presença de Deus. A memória não é apenas arquivo do passado, mas o lugar onde "
            "Agostinho busca a Deus. Essa investigação prepara a conversão intelectual e "
            "espiritual narrada ao longo da obra, culminando na afirmação de que o coração "
            "humano está inquieto até que descanse em Deus."
        ),
        "student_level": "superior",
        "subset": "qa",
        "gutenberg_id": 3296,
    },
 
    # TOMÁS DE AQUINO
    {
        "question": "Quais são as Cinco Vias de Tomás de Aquino para provar a existência de Deus?",
        "book_title": "Summa Theologica",
        "ground_truth": (
            "Na Suma Teológica (Questão 2, Artigo 3), Tomás de Aquino apresenta cinco "
            "argumentos cosmológicos: (1) Via do Movimento — tudo que se move é movido por "
            "outro, logo há um Primeiro Motor Imóvel. (2) Via da Causa Eficiente — há uma "
            "Causa Primeira incausada. (3) Via da Contingência — seres contingentes dependem "
            "de um Ser Necessário. (4) Via dos Graus de Perfeição — graus de bondade "
            "pressupõem um máximo absoluto. (5) Via do Governo do Mundo — a ordem "
            "teleológica da natureza aponta para um Inteligente ordenador. Todas as vias "
            "convergem para o que todos chamam de Deus."
        ),
        "student_level": "superior",
        "subset": "qa",
        "gutenberg_id": 17611,
    },
 
    # KIERKEGAARD
    {
        "question": "O que Kierkegaard entende por suspensão teleológica da ética em Temor e Tremor?",
        "book_title": "Fear and Trembling",
        "ground_truth": (
            "Em Temor e Tremor, Kierkegaard analisa o episódio bíblico do sacrifício de "
            "Isaque por Abraão. O cavaleiro da fé — Abraão — obedece a uma ordem divina "
            "que contradiz a ética universal (não matar o filho). Isso configura uma "
            "suspensão teleológica da ética: o indivíduo, por força de sua relação "
            "absoluta com o Absoluto, pode estar acima da norma ética geral. É o paradoxo "
            "da fé: a exigência divina individual supera a obrigação ética universal, "
            "algo incomunicável racionalmente."
        ),
        "student_level": "superior",
        "subset": "qa",
        "gutenberg_id": 50319,
    },
    {
        "question": "Quais são os três estádios da existência em Kierkegaard?",
        "book_title": "Either/Or",
        "ground_truth": (
            "Kierkegaard descreve três estádios (ou esferas) da existência: (1) Estádio "
            "Estético — o indivíduo vive para o prazer imediato, a beleza e a sensação; "
            "representado pelo sedutor de Ou-Ou. (2) Estádio Ético — o indivíduo assume "
            "responsabilidades e deveres morais; representado pelo assessor Wilhelm. "
            "(3) Estádio Religioso — transcende a ética por um salto de fé absurdo diante "
            "de Deus; representado por Abraão em Temor e Tremor. A passagem entre estádios "
            "não é gradual, mas um salto existencial."
        ),
        "student_level": "superior",
        "subset": "qa",
        "gutenberg_id": 32970,
    },
 
    # NIETZSCHE
    {
        "question": "O que Nietzsche quer dizer com 'Deus está morto' em Assim Falou Zaratustra?",
        "book_title": "Thus Spoke Zarathustra",
        "ground_truth": (
            "A proclamação de que Deus está morto em Nietzsche não é um ateísmo trivial, "
            "mas o diagnóstico cultural de que os valores absolutos (Deus, verdade objetiva, "
            "moral cristã) perderam sua força vinculante na modernidade europeia. O homem "
            "moderno matou Deus ao abraçar a ciência e o humanismo secular, mas não criou "
            "novos valores para substituí-los — daí o niilismo. Zaratustra anuncia o "
            "Übermensch como aquele que cria novos valores a partir da Vontade de Potência, "
            "superando o niilismo reativo."
        ),
        "student_level": "superior",
        "subset": "qa",
        "gutenberg_id": 1998,
    },
    {
        "question": "O que é a moral de rebanho e a moral dos senhores em Nietzsche?",
        "book_title": "Beyond Good and Evil",
        "ground_truth": (
            "Em Para Além do Bem e do Mal e na Genealogia da Moral, Nietzsche distingue "
            "dois tipos de moral: (1) Moral dos Senhores — nascida dos nobres que chamam "
            "de bom tudo que afirma sua força e poder; o mau é simplesmente o fraco. "
            "(2) Moral dos Escravos (rebanho) — surgida do ressentimento dos fracos, que "
            "invertem os valores: o bom passa a ser humildade e sofrimento; o mal é o "
            "poderoso. Nietzsche vincula a moral judaico-cristã à moral escrava, "
            "criticando-a como transvaloração negativa da vida."
        ),
        "student_level": "superior",
        "subset": "qa",
        "gutenberg_id": 4363,
    },
 
    # DOSTOIÉVSKI
    {
        "question": "Qual é a teoria de Raskolnikov sobre homens extraordinários em Crime e Castigo?",
        "book_title": "Crime and Punishment",
        "ground_truth": (
            "Raskolnikov acredita que a humanidade se divide em homens ordinários, que "
            "devem obedecer às leis, e homens extraordinários, como Napoleão, que têm o "
            "direito de transgredir a moral comum em prol de um objetivo superior. Ele "
            "testa essa teoria ao assassinar a agiota Alena Ivanovna. No entanto, o peso "
            "psicológico da culpa destrói progressivamente sua convicção, e Dostoiévski "
            "usa o colapso de Raskolnikov para refutar o niilismo moral e o utilitarismo "
            "radical de sua época."
        ),
        "student_level": "medio",
        "subset": "qa",
        "gutenberg_id": 2554,
    },
    {
        "question": "O que é o Grande Inquisidor em Os Irmãos Karamazov?",
        "book_title": "The Brothers Karamazov",
        "ground_truth": (
            "O Grande Inquisidor é um poema em prosa narrado por Ivan Karamazov no "
            "Livro V de Os Irmãos Karamazov. Nele, Cristo retorna à Sevilha da Inquisição "
            "e é preso pelo Cardeal Inquisidor, que argumenta que a Igreja corrigiu o "
            "erro de Cristo ao aceitar as três tentações do diabo (pão, milagre, poder "
            "temporal). Segundo o Inquisidor, os homens não querem liberdade, mas "
            "segurança e autoridade. Cristo responde apenas com um beijo. O capítulo é "
            "uma das mais profundas reflexões sobre liberdade, fé e autoridade religiosa "
            "na literatura ocidental."
        ),
        "student_level": "superior",
        "subset": "qa",
        "gutenberg_id": 28054,
    },
    {
        "question": "Qual é o papel do subterrâneo na filosofia do Homem do Subterrâneo de Dostoiévski?",
        "book_title": "Notes from Underground",
        "ground_truth": (
            "Em Notas do Subterrâneo, o narrador anônimo rejeita o determinismo e o "
            "utilitarismo racional do século XIX, simbolizados pelo Palácio de Cristal. "
            "Para ele, o homem age irracionalmente por necessidade de afirmar sua vontade "
            "livre — mesmo que seja para o mal — como prova de que não é determinado pela "
            "razão. O subterrâneo é a metáfora do isolamento do indivíduo que recusa as "
            "ilusões do progresso. A obra antecipa o existencialismo e a crítica ao "
            "positivismo do século XIX."
        ),
        "student_level": "superior",
        "subset": "qa",
        "gutenberg_id": 600,
    },
 
    # TOLSTÓI
    {
        "question": "Qual é a crise espiritual de Tolstói descrita em Uma Confissão?",
        "book_title": "A Confession",
        "ground_truth": (
            "Em Uma Confissão, Tolstói narra sua crise espiritual no auge da fama "
            "literária, após Guerra e Paz e Anna Karenina. Tomado por uma angústia "
            "existencial sobre o sentido da vida, considerou o suicídio. Percebeu que a "
            "razão e a ciência não podiam responder à questão de por que viver. Encontrou "
            "resposta não nos intelectuais, mas na fé simples dos camponeses russos — uma "
            "fé irracional mas vital. A obra marca sua virada para um cristianismo radical "
            "e não eclesiástico, que influenciou Gandhi e outros pensadores."
        ),
        "student_level": "superior",
        "subset": "qa",
        "gutenberg_id": 20203,
    },
 
    # GUIAS DE ESTUDO (subset = guide)
    {
        "question": "Gere um guia de estudo d'A República de Platão para o ensino superior.",
        "book_title": "The Republic",
        "ground_truth": (
            "Um guia de A República para o ensino superior deve cobrir: contexto histórico "
            "(Atenas pós-guerra do Peloponeso, morte de Sócrates); estrutura dos dez livros; "
            "a questão central sobre o que é a justiça; a Teoria das Formas e a Alegoria da "
            "Caverna (Livro VII); a divisão tripartite da alma (razão, ânimo, apetite) e "
            "sua correspondência com as classes da cidade ideal (filósofos, guerreiros, "
            "artesãos); a crítica à democracia e à arte; o mito de Er; comparação com "
            "Aristóteles na Política; perguntas dissertativas sobre justiça, poder e "
            "educação filosófica."
        ),
        "student_level": "superior",
        "subset": "guide",
        "gutenberg_id": 1497,
    },
    {
        "question": "Gere um guia de estudo da Ética a Nicômaco de Aristóteles para leitores iniciantes.",
        "book_title": "Nicomachean Ethics",
        "ground_truth": (
            "Um guia da Ética a Nicômaco para iniciantes deve apresentar: quem foi "
            "Aristóteles e sua relação com Platão; o conceito de eudaimonia explicado de "
            "forma acessível como viver bem e agir bem; a doutrina do justo meio com "
            "exemplos práticos (coragem entre covardia e temeridade); a diferença entre "
            "virtudes intelectuais e morais; a importância da amizade (philia) como bem "
            "supremo da vida social; como adquirir virtudes pelo hábito; e atividades de "
            "reflexão pessoal sobre próprias virtudes e vícios."
        ),
        "student_level": "fundamental",
        "subset": "guide",
        "gutenberg_id": 8438,
    },
    {
        "question": "Gere um guia de estudo de Assim Falou Zaratustra de Nietzsche para o ensino médio.",
        "book_title": "Thus Spoke Zarathustra",
        "ground_truth": (
            "Um guia de Assim Falou Zaratustra para o ensino médio deve incluir: "
            "breve biografia de Nietzsche e contexto do século XIX; estrutura da obra "
            "(quatro partes, estilo profético); os conceitos centrais — morte de Deus, "
            "Übermensch, Eterno Retorno, Vontade de Potência — com exemplos e analogias; "
            "os três estágios do espírito (camelo, leão, criança); o personagem Zaratustra "
            "como professor e profeta; trechos selecionados para leitura comentada; "
            "perguntas de reflexão sobre valores pessoais e sentido da vida; e um aviso "
            "sobre as distorções históricas do pensamento de Nietzsche."
        ),
        "student_level": "medio",
        "subset": "guide",
        "gutenberg_id": 1998,
    },
    {
        "question": "Gere um guia de estudo d'Os Irmãos Karamazov de Dostoiévski para o ensino superior.",
        "book_title": "The Brothers Karamazov",
        "ground_truth": (
            "Um guia d'Os Irmãos Karamazov para o ensino superior deve abranger: contexto "
            "da Rússia czarista e da crise de fé do século XIX; os três irmãos como "
            "tipologias humanas (Dmitri — paixão, Ivan — razão e niilismo, Aliocha — fé); "
            "o parricídio como estrutura dramática e simbólica; o capítulo do Grande "
            "Inquisidor e seu debate sobre liberdade e autoridade; o problema do mal "
            "e a revolta de Ivan; a redenção pelo sofrimento no arco de Dmitri; influência "
            "de Dostoiévski no existencialismo e na teologia do século XX; perguntas "
            "dissertativas sobre fé, razão e livre-arbítrio."
        ),
        "student_level": "superior",
        "subset": "guide",
        "gutenberg_id": 28054,
    },
]