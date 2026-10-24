import "./Nutrition.css";

// Nutrition per serving from INDB. Always labelled an estimate, never written by the AI.
export default function Nutrition({ n }) {
  return (
    <section className="nutrition">
      <h2>Nutrition per {n.per.replace(/^1 /, "")}, estimate</h2>
      <dl>
        <div>
          <dt>Energy</dt>
          <dd>{Math.round(n.kcal)} kcal</dd>
        </div>
        <div>
          <dt>Protein</dt>
          <dd>{n.protein_g} g</dd>
        </div>
        <div>
          <dt>Carbs</dt>
          <dd>{n.carbs_g} g</dd>
        </div>
        <div>
          <dt>Fat</dt>
          <dd>{n.fat_g} g</dd>
        </div>
        <div>
          <dt>Fibre</dt>
          <dd>{n.fibre_g} g</dd>
        </div>
      </dl>
    </section>
  );
}
