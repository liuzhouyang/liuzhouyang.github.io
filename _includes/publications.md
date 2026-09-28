## Selected Publications

<small>
<a href="https://dblp.org/pid/332/8613" target="_blank" rel="noopener" data-goatcounter-click="publications-full-dblp">Full publication list on DBLP</a>
</small>

<style>
.pub-item {
  display: flex;
  gap: 18px;
  align-items: center;
  margin: 1.35rem 0 1.65rem 0;
}
.pub-teaser {
  flex: 0 0 190px;
  width: 190px;
  height: 108px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.pub-teaser > a {
  display: flex;
  width: 100%;
  height: 100%;
  align-items: center;
  justify-content: center;
}
.pub-teaser img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 4px;
}
.pub-body {
  flex: 1 1 auto;
  min-width: 0;
}
.pub-title {
  font-weight: 600;
  line-height: 1.35;
}
.pub-authors {
  margin-top: 0.18rem;
  line-height: 1.42;
}
.pub-venue {
  margin-top: 0.12rem;
}
.pub-links {
  margin-top: 0.28rem;
  font-size: 0.93em;
}
@media (max-width: 640px) {
  .pub-item { display: block; }
  .pub-teaser {
    width: min(100%, 300px);
    height: 150px;
    margin: 0 0 0.65rem 0;
  }
}
</style>

{% for item in site.data.publications %}
<div class="pub-item">
  {% if item.image %}
  <div class="pub-teaser">
    {% if item.pdf %}<a href="{{ item.pdf }}" target="_blank" rel="noopener" data-goatcounter-click="paper-{{ item.short_title | slugify }}">{% endif %}
      <img src="{{ item.image | relative_url }}" alt="Teaser for {{ item.title | escape }}">
    {% if item.pdf %}</a>{% endif %}
  </div>
  {% endif %}

  <div class="pub-body">
    <div class="pub-title">
      {% if item.pdf %}
        <a href="{{ item.pdf }}" target="_blank" rel="noopener" data-goatcounter-click="paper-{{ item.short_title | slugify }}">{{ item.title }}</a>
      {% else %}
        {{ item.title }}
      {% endif %}
    </div>

    <div class="pub-authors">{{ item.authors }}</div>

    <div class="pub-venue">
      <em>{{ item.conference_short }}</em>{% if item.year %}, {{ item.year }}{% endif %}
    </div>

    <div class="pub-links">
      {% if item.pdf %}<a href="{{ item.pdf }}" target="_blank" rel="noopener" data-goatcounter-click="paper-{{ item.short_title | slugify }}">[Paper]</a>{% endif %}
      {% if item.code %}&nbsp;<a href="{{ item.code }}" target="_blank" rel="noopener" data-goatcounter-click="code-{{ item.short_title | slugify }}">[Code]</a>{% endif %}
      {% if item.dblp %}&nbsp;<a href="{{ item.dblp }}" target="_blank" rel="noopener" data-goatcounter-click="dblp-{{ item.short_title | slugify }}">[DBLP]</a>{% endif %}
      {% if item.bibtex %}&nbsp;<a href="{{ item.bibtex }}" target="_blank" rel="noopener" data-goatcounter-click="bibtex-{{ item.short_title | slugify }}">[BibTeX]</a>{% endif %}
      {% if item.copy_bibtex %}
      &nbsp;<button
        type="button"
        class="inline-copy copy-bibtex"
        data-bibtex-id="bibtex-{{ item.short_title | slugify }}"
        data-goatcounter-click="copy-bibtex-{{ item.short_title | slugify }}">[Copy BibTeX]</button>
      <script type="text/plain" id="bibtex-{{ item.short_title | slugify }}">{{ item.copy_bibtex }}</script>
      {% endif %}
    </div>
  </div>
</div>
{% endfor %}
