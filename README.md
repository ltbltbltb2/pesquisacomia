# Pesquisa com IA

Site publicado: https://pesquisacomia.com.br

Domínio configurado: https://pesquisacomia.com.br (com e sem www)

Laboratório experimental e educacional de pesquisas conduzidas por inteligência artificial. Esta edição disponibiliza **sete artigos (01 a 07)** e dois suplementos. Não há revisão por pares ou validação científica humana declarada.

## Acervo

1. Clima e dengue nas capitais brasileiras.
2. ERA5-Land e calor extremo.
3. Prontidão analítica da DCA/Siconfi para estudo do VAAT.
4. TimesFM-3 e carga do SIN.
5. Gasolina comum e comparabilidade semanal.
6. Etanol e gasolina: preços médios e locais em 26 capitais.
7. Reincidência após retorno ao limite de DEC na distribuição de energia.

O artigo 3 é uma cópia pública com correção explícita de proveniência e uma nota ao final. Seus resultados foram preservados. Os demais PDFs correspondem aos arquivos finais sem alteração do conteúdo. `manifesto-arquivos.json` registra os hashes SHA-256 dos nove PDFs.

O pacote de reprodução 1.0.0 do artigo 5 está disponível em `artigo-05-reproducao-v1.0.0.zip`: código, protocolo, documentação e resultados de referência, com aquisição direta dos oito dados oficiais da ANP. Os demais pacotes ainda não integram esta edição. O código deste repositório corresponde ao **site**, com o pipeline científico do artigo 5 distribuído separadamente no ZIP.

## Execução local

Sem dependências para visualizar o site:

```sh
python3 -m http.server 4173
```

Abra http://localhost:4173. Os arquivos HTML, CSS e JavaScript são o código completo do site e podem ser editados diretamente.

## Publicação

Hospedagem estática com Cloudflare Workers Static Assets. `wrangler.jsonc` define a pasta de publicação. O repositório está conectado à Cloudflare para publicar atualizações da branch `main`. A publicação usa `npx wrangler deploy`, sem etapa de compilação. Os domínios são administrados no painel da Cloudflare. Nenhuma chave deve ser adicionada ao repositório.

## Proteção de transporte e conteúdo

O domínio principal e `www` usam a regra nativa **HTTPS obrigatório** da Cloudflare (308). `security-worker.mjs` também mantém o redirecionamento 308, nos domínios configurados. Ambos preservam caminhos, parâmetros e método HTTP. Nas respostas HTTPS, a camada aplica HSTS somente ao host visitado, proteção contra incorporação em frames, prevenção de interpretação incorreta de tipos e uma política de conteúdo restrita, inclusive nas respostas de validação do cache (304). Os PDFs mantêm seu tipo, conteúdo e cache. Requisições condicionais e Range são encaminhadas sem alterações.

A geração automática do `robots.txt` pela Cloudflare convertia seus redirecionamentos HTTP em respostas 200. A política que já era servida no domínio foi preservada integralmente em `robots-domain.json`, utilizado pelo Worker, e a geração automática foi desativada. A rota alternativa de hospedagem está desativada. Os controles de bloqueio de robôs não foram alterados; futuras atualizações do texto da política do domínio devem ser versionadas neste repositório.

A camada executa antes dos arquivos estáticos. No plano Workers Free, essas invocações usam o limite de 100 mil requisições por dia; os acessos deixam de seguir o caminho de entrega exclusivamente estática. O plano de hospedagem não foi alterado. Domínios adicionais precisam ser incluídos explicitamente na lista de hosts permitidos.

Verificação local: `node --test security-worker.test.mjs`. A política não inclui analytics, novos serviços ou configurações de autenticação das contas.

## Contribuições

Use Issues para relatar reproduções e divergências. Informe estudo, versão, ambiente, passos e evidências. Não inclua credenciais, dados pessoais ou conteúdo confidencial.

## Proveniência e uso

Produção científica por IA, segundo a declaração do responsável pelo projeto. Iniciativa, infraestrutura e publicação humanas. A inclusão neste repositório não certifica a validade científica do conteúdo. Referências e fontes de terceiros mantêm suas condições próprias. Esta edição não concede uma licença geral sobre esses materiais.

## Navegação e conferência de arquivos

A busca combina termos, fontes e números de artigo; a URL conserva a busca e o tema ao voltar. Um estudo pode pertencer a mais de um tema. `grafico-gasolina.html` oferece ampliação e valores agregados da figura já publicada. `integridade.html` compara PDFs localmente com o SHA-256 do manifesto; não envia o arquivo selecionado a um servidor. Os manuscritos, suplementos e a camada de segurança foram preservados.

## Verificação de privacidade antes de publicar

O comando de build definido no Wrangler executa `privacy-build.mjs`, que instala o leitor PDF com versão e hashes fixados e roda `privacy-check.py` antes do envio dos assets. O build exige a configuração privada `PRIVACY_DENY_TERMS`, uma lista JSON de termos que não podem ser publicados. Essa lista fica nas configurações de build da hospedagem, nunca no repositório. A ausência da política, um erro de leitura ou uma correspondência impede a publicação. Os logs não imprimem os termos nem trechos dos documentos.

`privacy-approved-media.json` registra os PDFs, imagens e ZIPs já submetidos à auditoria de privacidade. Uma mídia nova ou alterada exige nova revisão integral de texto, imagens, metadados, links e objetos; somente depois deve ser atualizado esse registro. O gerador não aprova automaticamente novos arquivos. O manifesto de downloads também precisa corresponder aos bytes finais.

O endereço alternativo e as URLs de prévia estão desativados explicitamente na configuração. Somente os domínios próprios são aceitos pelo Worker. Os arquivos de verificação, ambientes de build, bundles e configurações estão excluídos dos assets.

O artigo 3 teve seus metadados de autoria removidos, com comparação de todas as páginas antes e depois, preservando texto, renderização e links. As versões de seus arquivos de download e respectivos hashes devem permanecer coerentes em cada revisão.

## Pacote de reprodução do artigo 5

Instruções e download: https://pesquisacomia.com.br/pesquisa-05.html#reproducao. Linux x86_64, Python 3.14, internet e pelo menos 1 GiB livre. As oito fontes são baixadas diretamente da ANP com tamanho e SHA-256 obrigatórios; arquivos divergentes interrompem a análise. O ZIP contém MIT para o código próprio e CC BY 4.0 para texto e figuras próprios, com atribuição a Pesquisa com IA. Dados e bibliotecas de terceiros ficam fora dessas concessões.

A validação local compara 27 resultados e figuras, 17 verificações de recálculo e seis de duplicatas. Não representa reprodução por pesquisador humano externo. O build inspeciona cada membro do ZIP, inclusive PDF e metadados de PNG, e exige aprovação do hash integral. Arquivos inesperados, caminhos inseguros, arquivos compactados aninhados e expansão excessiva bloqueiam a publicação.
