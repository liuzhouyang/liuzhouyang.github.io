## Selected Publications

<small>
<a href="https://dblp.org/pid/332/8613" target="_blank" rel="noopener">Full publication list on DBLP</a>
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
}
.pub-teaser img {
  display: block;
  width: 100%;
  height: auto;
  max-height: 125px;
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
    margin: 0 0 0.65rem 0;
  }
  .pub-teaser img { max-height: 170px; }
}
</style>

{% for item in site.data.publications %}
<div class="pub-item">
  {% if item.image %}
  <div class="pub-teaser">
    {% if item.pdf %}<a href="{{ item.pdf }}" target="_blank" rel="noopener">{% endif %}
      <img src="{{ item.image | relative_url }}" alt="Teaser for {{ item.title | escape }}">
    {% if item.pdf %}</a>{% endif %}
  </div>
  {% endif %}

  <div class="pub-body">
    <div class="pub-title">
      {% if item.pdf %}
        <a href="{{ item.pdf }}" target="_blank" rel="noopener">{{ item.title }}</a>
      {% else %}
        {{ item.title }}
      {% endif %}
    </div>

    <div class="pub-authors">{{ item.authors }}</div>

    <div class="pub-venue">
      <em>{{ item.conference_short }}</em>{% if item.year %}, {{ item.year }}{% endif %}
    </div>

    <div class="pub-links">
      {% if item.pdf %}<a href="{{ item.pdf }}" target="_blank" rel="noopener">[Paper]</a>{% endif %}
      {% if item.code %}&nbsp;<a href="{{ item.code }}" target="_blank" rel="noopener">[Code]</a>{% endif %}
      {% if item.dblp %}&nbsp;<a href="{{ item.dblp }}" target="_blank" rel="noopener">[DBLP]</a>{% endif %}
      {% if item.bibtex %}&nbsp;<a href="{{ item.bibtex }}" target="_blank" rel="noopener">[BibTeX]</a>{% endif %}
    </div>
  </div>
</div>
{% endfor %}
