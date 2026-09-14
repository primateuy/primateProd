/**
 * Contrato común de las vistas del dashboard. La clásica y la moderna reciben
 * exactamente esto del componente raíz, y cambiar de vista no recarga nada.
 */
export const dashboardViewProps = {
	data: Object,
	rows: Array,
	hasMoreRows: Boolean,
	loadingMore: Boolean,
	onOpenProject: Function,
	onLoadMore: Function,
	onOpenAreaTasks: Function,
	onOpenAlertRecord: Function,
	onSnooze: Function,
};
