# Recursos e Datasets de Fauna Brasileira

Aqui estão listadas as fontes recomendadas para fine-tuning do YOLOv8 em contexto de rodovias brasileiras.

## 1. Datasets Prontos (YOLO/COCO)

### BRAGAN (Brazilian Roadkill Animals)
- **Descrição:** Dataset especializado em animais atropelados no Brasil. Contém imagens reais e geradas por GAN.
- **Espécies:** Anta, Lobo-guará, Tamanduá-bandeira, Jaguatirica, Puma.
- **Link:** [Mendeley Data - BRA-Dataset](https://data.mendeley.com/datasets/ck88dwffgd/2)
- **Licença:** CC BY 4.0

### Roboflow Universe
- [Capybara (Capivara) Dataset](https://universe.roboflow.com/search?q=capybara)
- [Anteater (Tamanduá) Dataset](https://universe.roboflow.com/search?q=anteater)
- [Ocelot (Jaguatirica) Dataset](https://universe.roboflow.com/search?q=ocelot)

---

## 2. Projetos Acadêmicos e Monitoramento

### Sistema Urubu (CBEE - Centro Brasileiro de Ecologia de Estradas)
- **Coordenador:** Dr. Alex Bager (UFLA).
- **Descrição:** O maior projeto de ciência cidadã sobre atropelamentos no Brasil.
- **Site:** [sistemaurubu.com.br](http://sistemaurubu.com.br/)
- **Dica:** Através do aplicativo "Urubu Mobile", milhares de fotos são coletadas. Para fins acadêmicos sérios, é possível solicitar acesso ao banco de dados via parceria.

### Rede Brasileira de Especialistas em Ecologia de Transportes (REBIVAS)
- Grupo que reúne os principais pesquisadores da área. Útil para encontrar publicações recentes com novos datasets.
- **Site:** [rebivas.org.br](https://rebivas.org.br/)

---

## 3. APIs para Coleta de Grande Volume

### iNaturalist (api.inaturalist.org)
- **Uso:** Coleta de imagens de animais vivos (habitat natural).
- **Estratégia:** Baixar ~100 fotos de cada espécie alvo para ensinar ao modelo a "forma" do animal antes de focar no contexto de estrada.

### GBIF (Global Biodiversity Information Facility)
- **Uso:** Semelhante ao iNaturalist, mas agrega dados de museus e outras instituições.
- **Site:** [gbif.org](https://www.gbif.org/)

---

## Dica para Fine-Tuning
Como o seu modelo já foi treinado no COCO, ele já conhece "cachorro" e "gato".
- Mapeie `cachorro-do-mato` para uma classe nova ou use a classe `animal` genérica se o objetivo for apenas frenagem/alerta.
- Se for usar as classes solicitadas (`animal_wild`, `animal_domestic`, etc), use o script `scripts/dataset_unifier.py` para converter os datasets baixados.
