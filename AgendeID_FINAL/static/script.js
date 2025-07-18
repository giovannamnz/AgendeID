class AgendeIDApp {
    constructor() {
        this.state = {
            processando: false,
            usuarioLogado: false,
            tipoUsuario: null,
            conexaoStatus: true,
            historico: [],
            parametros: {},
            tentativasReconexao: 0,
            maxTentativasReconexao: 3,
            modoAtual: null 
        };

        this.elementos = {};
        this.init();
    }

    init() {
        this.bindElements();
        this.setupEventListeners();
        this.verificarConexao();
        this.verificarSessao();
        this.mostrarMensagemInicial();
        
        if (this.elementos.chatInput) {
            this.elementos.chatInput.focus();
        }
    }

    bindElements() {
        this.elementos = {
            chatForm: document.getElementById('chat-form'),
            chatInput: document.getElementById('chat-input'),
            chatBox: document.getElementById('chat-box'),
            sendButton: document.getElementById('send-button'),
            sendText: document.getElementById('send-text'),
            loadingSpinner: document.getElementById('loading-spinner'),
            statusConnection: document.getElementById('status-connection'),
            suggestions: document.getElementById('chat-suggestions'),
            sidebarContent: document.getElementById('sidebar-content'),
            chatHeader: document.querySelector('.chat-header')
        };
    }

    setupEventListeners() {
        if (this.elementos.chatForm) {
            this.elementos.chatForm.addEventListener('submit', (e) => this.enviarMensagem(e));
        }

        if (this.elementos.chatInput) {
            this.elementos.chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    if (!this.state.processando) {
                        this.enviarMensagem(e);
                    }
                }
            });

            this.elementos.chatInput.addEventListener('input', this.autoResizeInput.bind(this));
        }

        document.addEventListener('keydown', this.handleKeyboardShortcuts.bind(this));
        
        setInterval(() => this.verificarConexao(), 30000);

        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.verificarConexao();
            }
        });

        window.addEventListener('unhandledrejection', (event) => {
            console.error('Erro não tratado:', event.reason);
            this.adicionarMensagem('bot', 'Ocorreu um erro inesperado. Tente recarregar a página.');
        });
    }

async enviarMensagem(evento) {
    if (evento) evento.preventDefault();

    const mensagem = this.elementos.chatInput.value.trim();
    if (!mensagem || this.state.processando) return;

    if (mensagem.length > 1000) {
        this.adicionarMensagem('bot', 'Mensagem muito longa. Limite de 1000 caracteres.');
        return;
    }

    // Verificar se é comando de cadastro ou login
    if (mensagem.toLowerCase().includes('cadastro')) {
        this.iniciarCadastro();
    } else if (mensagem.toLowerCase().includes('login')) {
        this.iniciarLogin();
    }

    this.adicionarMensagem('user', mensagem);
    this.elementos.chatInput.value = '';
    this.autoResizeInput();
    this.ocultarSugestoes();
    this.definirEstadoCarregamento(true);

    this.state.historico.push({ 
        tipo: 'user', 
        mensagem, 
        timestamp: new Date() 
    });

    try {
        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        };

        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }

        const resposta = await fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken 
        },
        body: JSON.stringify({ mensagem })
        });


        const dados = await resposta.json();
        this.processarResposta(dados);
        this.state.tentativasReconexao = 0; 

    } catch (erro) {
        console.error('Erro na comunicação:', erro);
        this.tratarErroRequisicao(erro);
    } finally {
        this.definirEstadoCarregamento(false);
        if (this.elementos.chatInput) {
            this.elementos.chatInput.focus();
        }
    }
}

    iniciarCadastro() {
        this.state.modoAtual = 'cadastro';
        this.criarSidebarCadastro();
    }

    iniciarLogin() {
        this.state.modoAtual = 'login';
        this.criarSidebarLogin();
    }

    criarSidebarCadastro() {
        const html = `
            <h2>Status do Cadastro</h2>
            <ul style="list-style: none; padding: 0;">
                <li style="margin: 10px 0;"><span class="status" id="status-nome">⚠️ Nome</span></li>
                <li style="margin: 10px 0;"><span class="status" id="status-sexo">⚠️ Sexo</span></li>
                <li style="margin: 10px 0;"><span class="status" id="status-nacionalidade">⚠️ Nacionalidade</span></li>
                <li style="margin: 10px 0;"><span class="status" id="status-data_nascimento">⚠️ Data de Nascimento</span></li>
                <li style="margin: 10px 0;"><span class="status" id="status-nome_mae">⚠️ Nome da Mãe</span></li>
                <li style="margin: 10px 0;"><span class="status" id="status-cpf">⚠️ CPF</span></li>
                <li style="margin: 10px 0;"><span class="status" id="status-email">⚠️ Email</span></li>
            </ul>
        `;
        this.elementos.sidebarContent.innerHTML = html;
    }

    criarSidebarLogin() {
        const html = `
            <h2>Status do Login</h2>
            <ul style="list-style: none; padding: 0;">
                <li style="margin: 10px 0;"><span class="status" id="status-email">⚠️ Email</span></li>
                <li style="margin: 10px 0;"><span class="status" id="status-senha">⚠️ Senha</span></li>
            </ul>
        `;
        this.elementos.sidebarContent.innerHTML = html;
    }

    atualizarStatusParametros(parametros) {
        const nomesCampos = {
            nome: "Nome",
            sexo: "Sexo",
            nacionalidade: "Nacionalidade",
            data_nascimento: "Data de Nascimento",
            nome_mae: "Nome da Mãe",
            cpf: "CPF",
            email: "Email",
            senha: "Senha",
            telefone: "Telefone",
            tipo_usuario: "Tipo de Usuário"
        };

        for (let campo in parametros) {
            const statusElem = document.getElementById(`status-${campo}`);
            if (statusElem) {
                const valor = parametros[campo];
                const nomeVisivel = nomesCampos[campo] || campo;

                if (valor === "preenchido") {
                    statusElem.textContent = `✅ ${nomeVisivel}`;
                } else if (valor === "erro") {
                    statusElem.textContent = `❗ ${nomeVisivel}`;
                } else {
                    statusElem.textContent = `⚠️ ${nomeVisivel}`;
                }
            }
        }
    }


    processarResposta(dados) {
        try {
            console.log('Resposta do servidor:', dados);

            if (!dados || typeof dados !== 'object') {
                throw new Error('Formato de resposta inválido');
            }

            let mensagemBot = '';
            let parametros = {};
            let tipoMensagem = 'texto';
            
            if (dados.resposta !== undefined || dados.mensagem !== undefined) {
                mensagemBot = String(dados.resposta || dados.mensagem);
                parametros = dados.parametros || {};
                tipoMensagem = dados.tipo || 'texto';
            } else if (typeof dados === 'string') {
                mensagemBot = dados;
            } else {
                mensagemBot = 'Resposta do servidor em formato desconhecido';
                console.warn('Formato de resposta não reconhecido:', dados);
            }

            if (typeof mensagemBot === 'string' && mensagemBot.startsWith('__')) {
                this.processarComandoEspecial(mensagemBot, dados);
                return;
            }

            mensagemBot = this.sanitizarTexto(mensagemBot);

            this.adicionarMensagem('bot', mensagemBot);
            
            this.state.historico.push({
                tipo: 'bot',
                mensagem: mensagemBot,
                timestamp: new Date(),
                parametros,
                tipoMensagem
            });

            if (parametros && Object.keys(parametros).length > 0) {
                this.atualizarStatusParametros(parametros);
            }


            if (dados.redirect) {
                this.processarRedirecionamento(dados.redirect);
            }

            this.mostrarSugestoesContextuais(mensagemBot);
            this.atualizarStatusConexao(true);

            this.processarTipoMensagem(tipoMensagem, dados);

        } catch (erro) {
            console.error('Erro ao processar resposta:', erro);
            this.adicionarMensagem('bot', '❌ Erro ao processar resposta do servidor.');
            this.atualizarStatusConexao(false);
        }
    }

    tratarErroRequisicao(erro) {
        console.error('Detalhes do erro:', erro);
        
        let mensagemErro = 'Erro de comunicação. Tente novamente em alguns segundos.';
        this.adicionarMensagem('bot', mensagemErro);
        this.atualizarStatusConexao(false);

        if (this.state.modoAtual) {
            const campos = this.state.modoAtual === 'cadastro' 
                ? ['nome', 'email'] 
                : ['email', 'senha'];
            
            const parametrosErro = {};
            campos.forEach(campo => parametrosErro[campo] = 'erro');
            this.atualizarStatusParametros(parametrosErro);
        }
    }

    sanitizarTexto(texto) {
        return String(texto || '')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#x27;')
            .replace(/\n/g, '<br>');
    }

    processarTipoMensagem(tipo, dados) {
        switch(tipo) {
            case 'html':
                this.processarMensagemHTML(dados.mensagem);
                break;
            case 'opcoes':
                if (dados.opcoes) {
                    this.mostrarOpcoes(dados.opcoes);
                }
                break;
            case 'formulario':
                if (dados.campos) {
                    this.mostrarFormulario(dados.campos);
                }
                break;
            case 'erro':
                this.adicionarMensagem('bot', `${dados.mensagem}`);
                break;
            case 'sucesso':
                this.adicionarMensagem('bot', `${dados.mensagem}`);
                break;
        }
    }

    processarComandoEspecial(comando, dados) {
        const comandos = {
            '__cadastro_sucesso_funcionario__': () => {
                this.state.usuarioLogado = true;
                this.state.tipoUsuario = 'funcionario';
                this.adicionarMensagem('bot', 'Cadastro de funcionário realizado com sucesso!');
                this.redirecionarComContador('/painel_funcionario', 3);
            },
            '__login_sucesso_funcionario__': () => {
                this.state.usuarioLogado = true;
                this.state.tipoUsuario = 'funcionario';
                this.adicionarMensagem('bot', 'Login realizado com sucesso!');
                this.redirecionarComContador('/painel_funcionario', 2);
            },
            '__cadastro_sucesso_cliente__': () => {
                this.state.usuarioLogado = true;
                this.state.tipoUsuario = 'cliente';
                this.adicionarMensagem('bot', 'Cadastro de cliente realizado com sucesso!');
                this.redirecionarComContador('/painel_cliente', 3);
            },
            '__login_sucesso_cliente__': () => {
                this.state.usuarioLogado = true;
                this.state.tipoUsuario = 'cliente';
                this.adicionarMensagem('bot', 'Login realizado com sucesso!');
                this.redirecionarComContador('/painel_cliente', 2);
            },
            '__logout__': () => {
                this.state.usuarioLogado = false;
                this.state.tipoUsuario = null;
                this.adicionarMensagem('bot', 'Logout realizado com sucesso!');
                this.redirecionarComContador('/', 2);
            },
            '__erro_validacao__': () => {
                this.adicionarMensagem('bot', 'Erro de validação. Verifique os dados informados.');
            },
            '__sessao_expirada__': () => {
                this.state.usuarioLogado = false;
                this.state.tipoUsuario = null;
                this.adicionarMensagem('bot', ' Sua sessão expirou. Faça login novamente.');
            }
        };

        const handler = comandos[comando];
        if (handler) {
            handler();
        } else {
            this.adicionarMensagem('bot', comando.replace(/__/g, ''));
        }
    }

    adicionarMensagem(tipo, texto) {
        if (!this.elementos.chatBox) return;

        const mensagemDiv = document.createElement('div');
        mensagemDiv.className = `message ${tipo}`;
        mensagemDiv.innerHTML = this.processarTextoMensagem(texto);

        const timestamp = document.createElement('div');
        timestamp.className = 'timestamp';
        timestamp.textContent = this.formatarTimestamp(new Date());
        mensagemDiv.appendChild(timestamp);

        mensagemDiv.style.opacity = '0';
        mensagemDiv.style.transform = 'translateY(20px)';
        this.elementos.chatBox.appendChild(mensagemDiv);

        requestAnimationFrame(() => {
            mensagemDiv.style.transition = 'all 0.3s ease-out';
            mensagemDiv.style.opacity = '1';
            mensagemDiv.style.transform = 'translateY(0)';
        });

        this.scrollToBottom();
        
        this.limitarMensagensChat();
    }

    limitarMensagensChat(limite = 100) {
        if (this.elementos.chatBox.children.length > limite) {
            while (this.elementos.chatBox.children.length > limite) {
                this.elementos.chatBox.removeChild(this.elementos.chatBox.firstChild);
            }
        }
    }

    processarTextoMensagem(texto) {
        const textoSeguro = String(texto || '');
        
        return textoSeguro 
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/(https?:\/\/[^\s]+)/g, 
                '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
            );
    }

    formatarTimestamp(data) {
        return data.toLocaleTimeString('pt-BR', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }

    scrollToBottom() {
        if (this.elementos.chatBox) {
            this.elementos.chatBox.scrollTop = this.elementos.chatBox.scrollHeight;
        }
    }

    definirEstadoCarregamento(carregando) {
        this.state.processando = carregando;

        if (this.elementos.sendButton) {
            this.elementos.sendButton.disabled = carregando;
        }
        
        if (this.elementos.chatInput) {
            this.elementos.chatInput.disabled = carregando;
        }

        if (this.elementos.sendText && this.elementos.loadingSpinner) {
            this.elementos.sendText.style.display = carregando ? 'none' : 'inline';
            this.elementos.loadingSpinner.style.display = carregando ? 'inline' : 'none';
        }
    }

    atualizarStatusParametros(parametros) {
        const nomesCampos = {
            'nome': 'Nome',
            'sexo': 'Sexo',
            'nacionalidade': 'Nacionalidade',
            'data_nascimento': 'Data Nasc.',
            'nome_mae': 'Nome da Mãe',
            'cpf': 'CPF',
            'tipo_usuario': 'Tipo',
            'email': 'Email',
            'telefone': 'Telefone',
            'senha': 'Senha'
        };

        const icones = {
            'preenchido': '✅',
            'erro': '❌',
            'coletando': '🔄',
            'pendente': '⏳'
        };

        const cores = {
            'preenchido': '#10b981',
            'erro': '#ef4444',
            'coletando': '#3b82f6',
            'pendente': '#f59e0b'
        };

        Object.entries(parametros).forEach(([campo, status]) => {
            const elemento = document.getElementById(`status-${campo}`);
            if (!elemento) return;

            const nomeExibicao = nomesCampos[campo] || campo;
            const icone = icones[status] || '⏳';
            const cor = cores[status] || '#f59e0b';

            elemento.innerHTML = `${icone} ${nomeExibicao}`;
            elemento.style.color = cor;
            
            elemento.style.transform = 'scale(1.1)';
            setTimeout(() => {
                elemento.style.transform = 'scale(1)';
            }, 200);
        });

        this.state.parametros = { ...this.state.parametros, ...parametros };
    }

    mostrarSugestoesContextuais(mensagem) {
        if (!this.elementos.suggestions) return;

        this.elementos.suggestions.innerHTML = '';
        let sugestoes = [];

        if (!this.state.usuarioLogado) {
            sugestoes = [
                { texto: '🔑 Login', comando: 'Login' },
                { texto: '📝 Cadastro', comando: 'Cadastro' },
                { texto: '❓ Ajuda', comando: 'Ajuda' }
            ];
        } else if (this.state.tipoUsuario === 'cliente') {
            sugestoes = [
                { texto: '📅 Agendar', comando: 'Agendar atendimento' },
                { texto: '🔍 Consultar', comando: 'Consultar agendamentos' },
            ];
        } else if (this.state.tipoUsuario === 'funcionario') {
            sugestoes = [
                { texto: '📅 Agenda', comando: 'Ver agenda' },
                { texto: '✅ Confirmar', comando: 'Confirmar presença' },
                { texto: '📊 Relatório', comando: 'Gerar relatório' }
            ];
        }

        const mensagemLower = mensagem.toLowerCase();
        if (mensagemLower.includes('agendar') || mensagemLower.includes('marcar')) {
            sugestoes.push({ texto: ' Locais', comando: 'Ver locais disponíveis' });
        }
        
        if (mensagemLower.includes('cancelar')) {
            sugestoes.push({ texto: ' Suporte', comando: 'Falar com atendente' });
        }

        if (this.state.usuarioLogado) {
            sugestoes.push({ texto: ' Sair', comando: 'Logout' });
        }

        sugestoes.forEach(sugestao => {
            const botao = document.createElement('button');
            botao.className = 'suggestion-btn';
            botao.textContent = sugestao.texto;
            botao.onclick = () => this.enviarSugestao(sugestao.comando);
            this.elementos.suggestions.appendChild(botao);
        });

        this.elementos.suggestions.style.display = sugestoes.length > 0 ? 'flex' : 'none';
    }

    enviarSugestao(comando) {
        if (this.elementos.chatInput && !this.state.processando) {
            this.elementos.chatInput.value = comando;
            if (this.elementos.chatForm) {
                this.elementos.chatForm.dispatchEvent(new Event('submit'));
            }
        }
    }

    ocultarSugestoes() {
        if (this.elementos.suggestions) {
            this.elementos.suggestions.style.display = 'none';
        }
    }

    async verificarConexao() {
        try {
            // Simulando verificação de conexão
            this.atualizarStatusConexao(true);
        } catch (erro) {
            console.warn('Erro ao verificar conexão:', erro);
            this.atualizarStatusConexao(false);
        }
    }

    atualizarStatusConexao(conectado) {
        if (this.elementos.statusConnection) {
            this.elementos.statusConnection.textContent = 
                conectado ? '🟢 Conectado' : '🔴 Desconectado';
            this.elementos.statusConnection.style.color = 
                conectado ? '#10b981' : '#ef4444';
        }
        this.state.conexaoStatus = conectado;
    }

    async verificarSessao() {
        try {
            // Simulando verificação de sessão
            console.log('Verificando sessão...');
        } catch (erro) {
            console.warn('Erro ao verificar sessão:', erro);
            this.state.usuarioLogado = false;
            this.state.tipoUsuario = null;
        }
    }

    redirecionarComContador(url, segundos = 3) {
        let contador = segundos;
        const intervalId = setInterval(() => {
            if (contador <= 0) {
                clearInterval(intervalId);
                window.location.href = url;
            } else {
                this.adicionarMensagem('system', 
                    `🔄 Redirecionando em ${contador} segundo${contador > 1 ? 's' : ''}...`);
                contador--;
            }
        }, 1000);
    }

    processarRedirecionamento(url) {
        this.adicionarMensagem('system', '🔄 Redirecionando...');
        setTimeout(() => {
            window.location.href = url;
        }, 1500);
    }

    mostrarMensagemInicial() {
        if (this.elementos.chatBox && this.elementos.chatBox.children.length === 0) {
            const paginaAtual = window.location.pathname;
            
            let mensagemInicial = '';
            
            if (paginaAtual.includes('funcionario')) {
                mensagemInicial = `
                    <strong>Bem-vindo ao painel do funcionário!</strong><br><br>
                    Comandos disponíveis:<br>
                    • "ver agenda" - Visualizar agenda do dia<br>
                    • "confirmar presença [email]" - Confirmar cliente<br>
                    • "gerar relatório" - Relatório de atendimentos<br>
                    • "buscar cliente [CPF/email]" - Consultar cliente<br>
                    • "logout" - Sair do sistema
                `;
            } else if (paginaAtual.includes('cliente')) {
                mensagemInicial = `
                    <strong>Bem-vindo(a) ao painel do cliente!</strong><br><br>
                    Como posso ajudar você hoje?<br>
                    • Use o menu ao lado ou digite seu comando
                `;
            } else {
                mensagemInicial = `
                    <strong>Olá! Bem-vindo ao AgendeID!</strong><br><br>
                    Para começar, digite:<br>
                    • <strong>"Login"</strong> - se você já tem cadastro<br>
                    • <strong>"Cadastro"</strong> - para criar uma nova conta<br><br>
                    Estou aqui para ajudar com agendamentos de identidade! 😊
                `;
            }
            
            this.adicionarMensagem('bot', mensagemInicial);
        }
    }

    autoResizeInput() {
        if (this.elementos.chatInput) {
            this.elementos.chatInput.style.height = 'auto';
            this.elementos.chatInput.style.height = 
                Math.min(this.elementos.chatInput.scrollHeight, 120) + 'px';
        }
    }

    handleKeyboardShortcuts(e) {
        if (e.ctrlKey && e.key === 'l' && window.location.hostname === 'localhost') {
            e.preventDefault();
            this.limparChat();
        }
        
        if (e.key === 'Escape' && this.elementos.chatInput) {
            this.elementos.chatInput.focus();
        }
        
        if (e.ctrlKey && e.key === 'Enter' && !this.state.processando) {
            this.enviarMensagem();
        }
    }

    limparChat() {
        if (this.elementos.chatBox) {
            this.elementos.chatBox.innerHTML = '';
            this.state.historico = [];
            this.mostrarMensagemInicial();
        }
    }

    processarMensagemHTML(html) {
        console.log('Processando mensagem HTML:', html);
    }

    mostrarOpcoes(opcoes) {
        console.log('Mostrando opções:', opcoes);
    }

    mostrarFormulario(campos) {
        console.log('Mostrando formulário:', campos);
    }

    obterEstadoAtual() {
        return {
            ...this.state,
            historicoCount: this.state.historico.length,
            mensagensChat: this.elementos.chatBox ? this.elementos.chatBox.children.length : 0
        };
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.agendeID = new AgendeIDApp();
});

if (typeof module !== 'undefined' && module.exports) {
    module.exports = AgendeIDApp;
}