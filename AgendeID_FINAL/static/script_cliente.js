// Seleciona os elementos do DOM
const formularioChat = document.getElementById('chat-form');
const campoEntrada = document.getElementById('chat-input');
const caixaConversa = document.getElementById('chat-box');

// Estado que controla se uma mensagem está sendo processada
let processandoMensagem = false;

// Ao carregar a página, foca no campo de entrada e verifica a sessão do usuário
document.addEventListener('DOMContentLoaded', () => {
    campoEntrada.focus();
    verificarSessao();
});

// Envia a mensagem ao pressionar "Enter" no formulário
formularioChat.addEventListener('submit', enviarMensagem);

// Função principal de envio de mensagem para o backend
async function enviarMensagem(evento) {
    evento.preventDefault();

    const mensagem = campoEntrada.value.trim();
    if (!mensagem || processandoMensagem) return;

    adicionarMensagem('user', mensagem);
    campoEntrada.value = '';
    processandoMensagem = true;

    const indicadorCarregamento = adicionarIndicadorCarregamento();

    try {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        };
        if (csrfToken) headers['X-CSRFToken'] = csrfToken;

        const resposta = await fetch('/chat', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ mensagem }),
            credentials: 'same-origin'
        });

        removerIndicadorCarregamento(indicadorCarregamento);

        if (!resposta.ok) {
            let textoErro;
            try {
                const dadosErro = await resposta.json();
                textoErro = dadosErro.resposta || dadosErro.error || `HTTP ${resposta.status}: ${resposta.statusText}`;
            } catch {
                textoErro = await resposta.text() || `HTTP ${resposta.status}: ${resposta.statusText}`;
            }
            throw new Error(textoErro);
        }

        const dados = await resposta.json();
        if (dados.resposta) adicionarMensagem('bot', dados.resposta);

        if (dados.logout) {
            setTimeout(() => window.location.href = '/', 2000);
        }

        if (dados.redirect) {
            setTimeout(() => window.location.href = dados.redirect, 2000);
        }

    } catch (erro) {
        removerIndicadorCarregamento(indicadorCarregamento);

        let mensagemErro = 'Erro na comunicação com o servidor';

        if (erro.name === 'TypeError' && erro.message.includes('fetch')) {
            mensagemErro = 'Servidor não está respondendo. Verifique sua conexão.';
        } else if (erro.message.includes('400')) {
            mensagemErro = 'Dados da requisição inválidos.';
        } else if (erro.message.includes('403')) {
            mensagemErro = 'Acesso negado. Faça login novamente.';
            setTimeout(() => window.location.href = '/', 3000);
        } else if (erro.message.includes('500')) {
            mensagemErro = 'Erro interno do servidor.';
        } else if (erro.message.includes('429')) {
            mensagemErro = 'Muitas requisições. Aguarde um pouco.';
        } else if (erro.message) {
            mensagemErro = erro.message;
        }

        adicionarMensagem('bot', mensagemErro);
    } finally {
        processandoMensagem = false;
        campoEntrada.focus();
    }
}

// Adiciona uma nova mensagem ao chat
function adicionarMensagem(tipo, texto) {
    const div = document.createElement('div');
    div.className = `message ${tipo}`;

    if (typeof texto === 'string') {
        const textoSeguro = texto
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;')
            .replace(/\n/g, '<br>');
        div.innerHTML = textoSeguro;
    } else {
        div.textContent = String(texto);
    }

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

// Mostra indicador "Processando..." no chat
function adicionarIndicadorCarregamento() {
    const div = document.createElement('div');
    div.className = 'message bot loading';
    div.innerHTML = 'Processando...';

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

// Remove o indicador de carregamento
function removerIndicadorCarregamento(elemento) {
    if (elemento?.parentNode) {
        elemento.parentNode.removeChild(elemento);
    }
}

// Verifica se o usuário ainda está logado
async function verificarSessao() {
    try {
        const resposta = await fetch('/verificar-sessao', {
            credentials: 'same-origin'
        });

        if (resposta.ok) {
            const data = await resposta.json();
            if (!data.logado) {
                window.location.href = '/';
                return;
            }
        }
    } catch (err) {
        console.error('Erro ao verificar sessão:', err);
    }
}

// Atalhos de teclado: ESC foca input, CTRL+Enter envia
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        campoEntrada.focus();
    }
    if (e.ctrlKey && e.key === 'Enter' && !processandoMensagem) {
        formularioChat.dispatchEvent(new Event('submit'));
    }
});

// Expondo função globalmente
window.verificarSessao = verificarSessao;

// Logs de diagnóstico
console.log('Script cliente carregado com sucesso!');
console.log('Função enviarSugestao disponível:', typeof enviarSugestao);

// Verificações de elementos ausentes
if (!formularioChat) console.error('Elemento #chat-form não encontrado!');
if (!campoEntrada) console.error('Elemento #chat-input não encontrado!');
if (!caixaConversa) console.error('Elemento #chat-box não encontrado!');
