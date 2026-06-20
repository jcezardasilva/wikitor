---
id: servidor-dns/configurando-um-servidor-dns-com-bind9-no-linux
titulo: Configurando um Servidor DNS com BIND9 no Linux
assunto: servidor-dns
nivel: intermediario
resumo: O BIND9 no Linux é configurado instalando o pacote, definindo zonas de domínio
  e criando arquivos de zona para gerenciar a tradução de nomes para IPs.
status: publicado
referencias: []
atualizado_em: '2026-06-20'
---

# Configurando um Servidor DNS com BIND9 no Linux

## 1. O que é DNS?

DNS (Domain Name System) é o sistema responsável por traduzir nomes de domínio legíveis por humanos (como `www.exemplo.local`) em endereços IP numéricos (como `192.168.1.10`), que são os endereços que os computadores usam para se comunicar na internet.

Em resumo, o DNS funciona como a "lista telefônica" da internet.

## 2. Configurando um Servidor DNS no Linux com BIND9

Para configurar um servidor DNS no Linux, usaremos o BIND9, que é um dos servidores DNS mais populares.

### 2.1. Instalação do BIND9

Primeiro, você precisa instalar o pacote BIND9 no seu sistema Linux.

**Exemplo (para sistemas baseados em Debian/Ubuntu):**

```bash
sudo apt update
sudo apt install bind9
```

### 2.2. Configuração Básica do Servidor

A configuração principal do BIND9 é feita através do arquivo de configuração principal, geralmente localizado em `/etc/bind/named.conf`.

Você precisará editar este arquivo para definir as zonas de domínio que seu servidor irá gerenciar.

### 2.3. Exemplo de Zona (Exemplo: `exemplo.local`)

Para que o servidor DNS resolva nomes dentro do seu domínio, você precisa definir uma zona. Abaixo está um exemplo de como configurar uma zona simples para o domínio `exemplo.local`.

**Caminho do arquivo de configuração (Exemplo):**

Você deve editar o arquivo de configuração principal (ou um arquivo de zona específico, dependendo da sua arquitetura).

**Exemplo de definição de zona (`named.conf.local`):**

```text
zone "exemplo.local" {
    type master;
    file "/etc/bind/db.exemplo.local";
};
```

### 2.4. Criação do Arquivo da Zona

O arquivo que contém os registros reais (como A, MX, NS) é criado separadamente. Para o domínio `exemplo.local`, o arquivo seria, por exemplo, `/etc/bind/db.exemplo.local`.

**Exemplo de conteúdo do arquivo de zona (`db.exemplo.local`):**

Este arquivo define a tradução dos nomes para os endereços IP.

```dns
; Zona para exemplo.local
name = exemplo.local
type = master
file .=zone
entropy = 168
ttl = 3600

; Registros de Zona
A    exemplo.local.    192.168.1.10  ; O servidor DNS resolve exemplo.local para este IP
NS   exemplo.local.    ns1.exemplo.local
SOA  ns1.exemplo.local. admin.exemplo.local. (
    \period    604800;
    \refresh   86400;
    \retry    1209600;
    \expire    604800;
    \timezone  "GMT-3";
);
```

### 2.5. Verificação e Reinício

Após editar os arquivos de configuração, você deve verificar a sintaxe da configuração e reiniciar o serviço do BIND9 para aplicar as mudanças.

**Verificação da sintaxe:**

```bash
sudo named-checkconf
sudo named-checkzone exemplo.local /etc/bind/db.exemplo.local
```

**Reiniciar o serviço:**

```bash
sudo systemctl restart bind9
```

Com isso, seu servidor DNS no Linux estará configurado para gerenciar as resoluções de nomes para o domínio `exemplo.local`.
