<script>
  // « Connexion » : une tuile par service. Gazette lit les sources libres et reçoit les séjours de
  // Home Assistant ; elle n'écrit chez aucun service.
  import { onMount } from 'svelte'
  import BookOpen from '@lucide/svelte/icons/book-open'
  import Globe from '@lucide/svelte/icons/globe'
  import Database from '@lucide/svelte/icons/database'
  import Library from '@lucide/svelte/icons/library'
  import House from '@lucide/svelte/icons/house'
  import FileText from '@lucide/svelte/icons/file-text'
  import BookUser from '@lucide/svelte/icons/book-user'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import { dateCourte } from '$lib/format.js'

  let { ondeconnecte } = $props()
  let e = $state(null)
  let sonde = $state(null)
  let choisi = $state(null)
  let attente = $state(false)

  async function lire() {
    try { e = await api.get('/api/connexion/etat') } catch (err) { if (err.statut === 401) ondeconnecte?.() }
  }
  async function verifier() {
    attente = true
    try { sonde = await api.post('/api/connexion/verifier') } catch { /* affiché par les voyants */ }
    attente = false
  }
  const services = $derived(e ? [
    { cle: 'wikipedia-fr', nom: 'Wikipédia FR', icone: BookOpen, cache: e.sources.wp, lit: 'pages « mois année », « année en France », « année », « jour mois » (wikitext brut)', ecrit: 'rien' },
    { cle: 'wikipedia-en', nom: 'Wikipédia EN', icone: Globe, cache: null, lit: 'pages « Month Year », en repli quand la semaine est pauvre ; proposées en anglais, jamais choisies seules', ecrit: 'rien' },
    { cle: 'wikidata', nom: 'Wikidata', icone: Database, cache: e.sources.wd, lit: 'notoriété des pages (liens interlangues) et nature « être humain »', ecrit: 'rien' },
    { cle: 'larousse', nom: 'Larousse', icone: Library, cache: e.sources.lar, lit: "Journaux de l'année, chronologie du mois (1966 à 2003). Textes non libres : usage familial, rien ne sort du NAS", ecrit: 'rien' },
    { cle: 'ha', nom: 'Home Assistant', icone: House, cache: null, lit: 'reçoit les séjours sur /ha/sejour (jeton GAZETTE_JETON_HA) ; HA lit /ha/etat', ecrit: 'rien' },
    { cle: 'carnet', nom: 'Carnet', icone: BookUser, cache: null, lit: 'noms et dates de naissance sur /gazette/personnes (jeton GAZETTE_CARNET_JETON, ou le jeton commun MAISON_JETON) : fiche créée seule pour un invité connu, saisie assistée, dates comparées', ecrit: 'rien' },
    { cle: 'rendu', nom: 'Rendu PDF', icone: FileText, cache: null, lit: 'Chromium dans le conteneur, polices embarquées', ecrit: 'rien' },
  ] : [])
  function voyant(s) {
    if (s.cle === 'ha') return e.ha.porte ? (e.ha.dernier_appel ? 'ok' : 'attente') : 'ko'
    if (s.cle === 'rendu') return e.rendu.polices ? 'ok' : 'ko'
    if (s.cle === 'carnet' && !sonde?.carnet) return !e.carnet.regle ? 'coupe' : e.carnet.erreur ? 'ko' : e.carnet.personnes !== null ? 'ok' : 'attente'
    if (s.cle === 'larousse' && !e.larousse) return 'coupe'
    if (sonde?.[s.cle]) return sonde[s.cle].ok ? 'ok' : sonde[s.cle].ok === null ? 'coupe' : 'ko'
    if (e.erreurs[s.cle]) return 'ko'
    return s.cache ? 'ok' : 'attente'
  }
  function detail(s) {
    if (s.cle === 'ha') return e.ha.porte ? (e.ha.dernier_appel ? `dernier séjour reçu ${dateCourte(e.ha.dernier_appel)}` : 'porte ouverte, rien reçu') : 'porte fermée (jeton absent)'
    if (s.cle === 'rendu') return e.rendu.polices ? 'polices présentes' : 'polices absentes'
    if (s.cle === 'carnet' && !sonde?.carnet) return !e.carnet.regle ? 'pas réglé (jeton absent)' : e.carnet.erreur ? e.carnet.erreur
      : e.carnet.personnes !== null ? `${e.carnet.personnes} contacts, ${e.carnet.dates} avec date complète` : 'pas encore lu'
    if (sonde?.[s.cle]) return sonde[s.cle].detail
    if (e.erreurs[s.cle]) return e.erreurs[s.cle]
    return s.cache ? `${s.cache.pages} pages gardées` : 'rien de lu pour l\'instant'
  }
  onMount(lire)
</script>

<header class="mb-5 flex flex-wrap items-end justify-between gap-3">
  <div>
    <p class="etiquette">Gazette</p>
    <h1 class="titre">Connexion</h1>
  </div>
  <Button variant="outline" onclick={verifier} disabled={attente}>{attente ? 'Vérification…' : 'Vérifier les sources'}</Button>
</header>

{#if e}
  <div class="grid grid-cols-2 gap-3 md:grid-cols-3" role="group" aria-label="Services">
    {#each services as s}
      {@const Icone = s.icone}
      {@const v = voyant(s)}
      <button type="button" aria-pressed={choisi === s.cle} onclick={() => (choisi = choisi === s.cle ? null : s.cle)}
              class="flex min-h-28 flex-col gap-1 rounded-2xl border bg-card p-4 text-left transition-colors hover:border-primary aria-pressed:border-primary">
        <span class="flex items-start justify-between">
          <Icone class="size-6 text-primary" aria-hidden="true" />
          <span class="size-2.5 rounded-full {v === 'ok' ? 'bg-valide' : v === 'ko' ? 'bg-destructive' : 'bg-muted-foreground/40'}" aria-label={v}></span>
        </span>
        <span class="font-medium">{s.nom}</span>
        <span class="text-sm text-muted-foreground">{detail(s)}</span>
      </button>
    {/each}
  </div>
  {#each services.filter((s) => s.cle === choisi) as s}
    <section class="mt-4 rounded-2xl border bg-card p-5" aria-label={s.nom}>
      <h2 class="text-lg font-semibold">{s.nom}</h2>
      <p class="mt-2 text-sm"><span class="text-muted-foreground">Lit :</span> {s.lit}</p>
      <p class="text-sm"><span class="text-muted-foreground">Écrit :</span> {s.ecrit}</p>
      {#if s.cle === 'ha' && e.ha.dernier_corps}<p class="mt-2 text-sm text-muted-foreground">Dernier appel : {e.ha.dernier_corps}</p>{/if}
    </section>
  {/each}
{:else}
  <p class="text-sm text-muted-foreground">Lecture…</p>
{/if}
