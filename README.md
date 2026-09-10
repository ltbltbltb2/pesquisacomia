# Pesquisa com IA

Site publicado: https://pesquisacomia.com.br

Domínio configurado: https://pesquisacomia.com.br (com e sem www)

Laboratório experimental e educacional de pesquisas conduzidas por inteligência artificial. Esta edição disponibiliza **cinco artigos (01 a 05)** e dois suplementos. Não há revisão por pares ou validação científica humana declarada.

## Acervo

1. Clima e dengue nas capitais brasileiras.
2. ERA5-Land e calor extremo.
3. Prontidão analítica da DCA/Siconfi para estudo do VAAT.
4. TimesFM-3 e carga do SIN.
5. Gasolina comum e comparabilidade semanal.

O artigo 3 é uma cópia pública com correção explícita de proveniência e uma nota ao final. Seus resultados foram preservados. Os demais PDFs correspondem aos arquivos finais sem alteração do conteúdo. `manifesto-arquivos.json` registra os hashes SHA-256 dos sete PDFs.

Os pacotes completos de dados, código analítico e ambiente não integram esta primeira edição. O código deste repositório corresponde ao **site**, não aos pipelines científicos dos artigos.

## Execução local

Sem dependências para visualizar o site:

```sh
python3 -m http.server 4173
```

Abra http://localhost:4173. Os arquivos HTML, CSS e JavaScript são o código completo do site e podem ser editados diretamente.

## Publicação

Hospedagem estática com Cloudflare Workers Static Assets. `wrangler.jsonc` define a pasta de publicação. O repositório está conectado à Cloudflare para publicar atualizações da branch `main`. A publicação usa `npx wrangler deploy`, sem etapa de compilação. Os domínios são administrados no painel da Cloudflare. Nenhuma chave deve ser adicionada ao repositório.

## Contribuições

Use Issues para relatar reproduções e divergências. Informe estudo, versão, ambiente, passos e evidências. Não inclua credenciais, dados pessoais ou conteúdo confidencial.

## Proveniência e uso

Produção científica por IA, segundo a declaração do responsável pelo projeto. Iniciativa, infraestrutura e publicação humanas. A inclusão neste repositório não certifica a validade científica do conteúdo. Referências e fontes de terceiros mantêm suas condições próprias. Esta edição não concede uma licença geral sobre esses materiais.
