/**
 * Small footer strip below the input, clarifying the assistant's scope
 * and grounding in Gadgets360 data.
 */
function Footer() {
  return (
    <div className="border-t border-ink-100 px-4 py-1.5 text-center dark:border-ink-800">
      <span className="text-[0.65rem] text-ink-400 dark:text-ink-500">
        Answers are generated from Gadgets360 data and may be incomplete.
      </span>
    </div>
  )
}

export default Footer
