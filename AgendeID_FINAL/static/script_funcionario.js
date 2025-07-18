// Seleciona os elementos do DOM necessários para o chat
const formularioChat = document.getElementById('chat-form');
const campoEntrada = document.getElementById('chat-input');
const caixaConversa = document.getElementById('chat-box');

// Controle de estado para evitar múltiplos envios
let processandoMensagem = false;

// Ao carregar a página, foca no input, verifica sessão e mostra mensagem inicial
document.addEventListener('DOMContentLoaded', () => {
    campoEntrada.focus();
    verificarSessao();
});

// Envia a mensagem quando o formulário for enviado
formularioChat.addEventListener('submit', enviarMensagem);

// Função que valida comandos específicos antes de enviar
function validarComando(mensagem) {
    const msgLower = mensagem.toLowerCase().trim();

    // Verifica comandos incompletos e retorna sugestão de uso
    if (msgLower === 'confirmar' || msgLower === 'confirmar presença') {
        return {
            valido: false,
            sugestao: ' Use: "confirmar presença [email]" ou "confirmar presença [ID]"\n\nExemplo: confirmar presença joao@email.com'
        };
    }

    if (msgLower === 'buscar cliente' || msgLower === 'buscar') {
        return {
            valido: false,
            sugestao: ' Use: "buscar cliente [CPF]" ou "buscar cliente [email]"\n\nExemplo: buscar cliente 123.456.789-00'
        };
    }

    if (msgLower.startsWith('buscar cliente ')) {
        const parametro = msgLower.replace('buscar cliente ', '').trim();
        const cpfRegex = /^\d{11}$|^\d{3}\.\d{3}\.\d{3}-\d{2}$/;
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if (!cpfRegex.test(parametro) && !emailRegex.test(parametro)) {
            return {
                valido: false,
                sugestao: ' Formato inválido!\n\nUse CPF (11 dígitos) ou email válido:\n• "buscar cliente 12345678901"\n• "buscar cliente usuario@email.com"'
            };
        }
    }

    return { valido: true };
}

// (OPCIONAL) Versão com validação isolada, mas atualmente não usada
async function enviarMensagemComValidacao(evento) {
    evento.preventDefault();
    const mensagem = campoEntrada.value.trim();
    if (!mensagem || processandoMensagem) return;

    const validacao = validarComando(mensagem);
    if (!validacao.valido) {
        adicionarMensagem('user', mensagem);
        adicionarMensagem('bot', validacao.sugestao);
        campoEntrada.value = '';
        return;
    }
}

// Envia a mensagem para o backend Flask
async function enviarMensagem(evento) {
    evento.preventDefault();

    const mensagem = campoEntrada.value.trim();
    if (!mensagem || processandoMensagem) return;

    adicionarMensagem('user', mensagem);
    campoEntrada.value = '';
    processandoMensagem = true;

    const loadingDiv = adicionarMensagem('bot', ' Processando...');

    try {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        if (!csrfToken) throw new Error('Token CSRF não encontrado');

        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'Accept': 'application/json'
            },
            body: JSON.stringify({ mensagem })
        });

        // Remove " Processando..." após resposta
        if (loadingDiv && loadingDiv.parentNode) {
            loadingDiv.parentNode.removeChild(loadingDiv);
        }

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Erro ${response.status}: ${response.statusText}`);
        }

        const contentType = response.headers.get('content-type');
        if (!contentType?.includes('application/json')) {
            const text = await response.text();
            throw new Error('Resposta inválida do servidor');
        }

        const dados = await response.json();

        if (dados.resposta) {
            adicionarMensagem('bot', dados.resposta);
            processarComandosFuncionario(mensagem, dados);

            if (dados.redirect) {
                setTimeout(() => {
                    window.location.href = dados.redirect;
                }, 2000);
            }
        } else {
            throw new Error('Resposta vazia do servidor');
        }

    } catch (erro) {
        console.error('Erro completo:', erro);

        const loadingElements = document.querySelectorAll('.message.bot:last-child');
        const lastElement = loadingElements[loadingElements.length - 1];
        if (lastElement && lastElement.textContent.includes('⏳')) {
            lastElement.parentNode.removeChild(lastElement);
        }

        let mensagemErro = 'Erro ao processar sua mensagem.';
        if (erro.message.includes('Token CSRF')) {
            mensagemErro = 'Erro de segurança. Recarregue a página.';
        } else if (erro.message.includes('400')) {
            mensagemErro = 'Requisição inválida. Verifique sua mensagem.';
        } else if (erro.message.includes('403')) {
            mensagemErro = 'Acesso negado. Faça login novamente.';
        } else if (erro.message.includes('500')) {
            mensagemErro = 'Erro interno do servidor. Tente novamente.';
        }

        adicionarMensagem('bot', mensagemErro);
    } finally {
        processandoMensagem = false;
    }
}

// Trata comandos que são exclusivos de funcionários
function processarComandosFuncionario(mensagem, dados) {
    const msgLower = mensagem.toLowerCase().trim();

    if (
        msgLower.includes('ver agenda') ||
        msgLower.includes('agenda hoje') ||
        msgLower.startsWith('confirmar') ||
        msgLower.includes('gerar relatório') ||
        msgLower.includes('gerar relatorio') ||
        msgLower.startsWith('buscar cliente')
    ) {
        return; 
    }
}

// Cria uma nova mensagem no chat
function adicionarMensagem(tipo, texto) {
    const div = document.createElement('div');
    div.className = `message ${tipo}`;
    const textoFormatado = String(texto || '').replace(/\n/g, '<br>');
    div.innerHTML = textoFormatado;

    const timestamp = document.createElement('div');
    timestamp.className = 'timestamp';
    timestamp.textContent = new Date().toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit'
    });

    div.appendChild(timestamp);
    caixaConversa.appendChild(div);
    caixaConversa.scrollTop = caixaConversa.scrollHeight;

    return div;
}

// Verifica se a sessão ainda está ativa (usado ao carregar a página)
function verificarSessao() {
    fetch('/verificar-sessao', {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
    })
        .then(res => {
            if (!res.ok) throw new Error(`Erro ${res.status}`);
            return res.json();
        })
        .then(data => {
            if (!data.logado || data.tipo !== 'funcionario') {
                console.log('Sessão inválida, redirecionando...');
                window.location.href = '/';
            }
        })
        .catch(error => {
            console.error("Erro ao verificar sessão:", error);
            adicionarMensagem('bot', 'Aviso: Não foi possível verificar sua sessão. Verifique sua conexão.');
        });
}

// Atalhos de teclado: ESC para foco, Ctrl+Enter para enviar
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && campoEntrada) {
        campoEntrada.focus();
    }
    if (e.ctrlKey && e.key === 'Enter' && !processandoMensagem) {
        enviarMensagem(e);
    }
});

// Função de debug visível apenas em ambiente local
function debug(message, data = null) {
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        console.log(`[DEBUG] ${message}`, data || '');
    }
}
