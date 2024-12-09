const { createApp } = Vue

const app = createApp({
    delimiters: ['[[', ']]'],
    compilerOptions: {
        isCustomElement: tag => tag.includes('-'),
        whitespace: 'preserve',
        comments: true
    },
    data() {
        return {
            nodes: [],
            error: null,
            modal: null,
            confirmModal: null,
            batchAddModal: null,
            currentNode: {
                name: '',
                node_type: 'variable',
                node_id: '',
                data_type: 'double',
                value: '',
                description: '',
                variation_type: 'none',
                variation_interval: 1000,
                variation_min: null,
                variation_max: null,
                variation_step: null,
                variation_values: '',
                decimal_places: 2
            },
            isEditMode: false,
            nodeIdError: '',
            isCheckingNodeId: false,
            formErrors: {
                name: '',
                nodeId: '',
                value: ''
            },
            confirmDialog: {
                title: '',
                message: '',
                callback: null,
                type: 'warning',
                iconClass: '',
                confirmText: '',
                node: null
            },
            valueRanges: {
                'int32': { min: -2147483648, max: 2147483647 },
                'int64': { min: -9223372036854775808n, max: 9223372036854775807n },
                'uint16': { min: 0, max: 65535 },
                'uint32': { min: 0, max: 4294967295 },
                'uint64': { min: 0n, max: 18446744073709551615n },
                'float': { min: -3.4e38, max: 3.4e38 },
                'double': { min: -1.8e308, max: 1.8e308 }
            },
            batchSettings: {
                nameTemplate: '',
                nodeIdTemplate: '',
                startIndex: 1,
                endIndex: 1,
                nodeType: 'variable',
                dataType: 'double',
                valueTemplate: '',
                variationType: 'none',
                variationMin: null,
                variationMax: null,
                variationStep: null,
                variationInterval: 1000,
                decimalPlaces: 2
            },
            batchErrors: {
                nameTemplate: '',
                nodeIdTemplate: '',
                range: '',
                value: '',
                duplicates: []
            },
            isProcessing: false,
            nodeTypes: [
                { value: 'variable', label: '变量' },
                { value: 'object', label: '对象' },
                { value: 'method', label: '方法' }
            ],
            dataTypes: [
                { value: 'double', label: '双精度浮点数(Double)' },
                { value: 'float', label: '单精度浮点数(Float)' },
                { value: 'int32', label: '32位整数(Int32)' },
                { value: 'int64', label: '64位整数(Int64)' },
                { value: 'uint16', label: '无符号16位整数(UInt16)' },
                { value: 'uint32', label: '无符号32位整数(UInt32)' },
                { value: 'uint64', label: '无符号64位整数(UInt64)' },
                { value: 'boolean', label: '布尔值(Boolean)' },
                { value: 'string', label: '字符串(String)' },
                { value: 'datetime', label: '日期时间(DateTime)' },
                { value: 'bytestring', label: '字节串(ByteString)' },
                { value: 'array', label: '数组(Array)' }
            ],
            variationTypes: [
                { value: 'none', label: '不变化' },
                { value: 'random', label: '随机变化' },
                { value: 'linear', label: '线性变化' },
                { value: 'discrete', label: '离散变化' },
                { value: 'cycle', label: '循环变化' }
            ]
        }
    },
    computed: {
        isFormValid() {
            return !this.formErrors.name && !this.formErrors.nodeId && !this.formErrors.value;
        },
        isBatchFormValid() {
            return !this.batchErrors.nameTemplate && !this.batchErrors.nodeIdTemplate && 
                   !this.batchErrors.range && !this.batchErrors.value && 
                   this.batchErrors.duplicates.length === 0;
        }
    },
    methods: {
        // 添加节点相关方法
        showAddNodeModal() {
            this.isEditMode = false;
            this.currentNode = {
                name: '',
                node_type: 'variable',
                node_id: '',
                data_type: 'double',
                value: '',
                description: '',
                variation_type: 'none',
                variation_interval: 1000,
                variation_min: null,
                variation_max: null,
                variation_step: null,
                variation_values: '',
                decimal_places: 2
            };
            this.nodeIdError = '';
            this.formErrors = {
                name: '',
                nodeId: '',
                value: ''
            };
            if (this.modal) {
                this.modal.show();
            }
        },
        showBatchAddModal() {
            this.batchSettings = {
                nameTemplate: '',
                nodeIdTemplate: '',
                startIndex: 1,
                endIndex: 1,
                nodeType: 'variable',
                dataType: 'double',
                valueTemplate: '',
                variationType: 'none',
                variationMin: null,
                variationMax: null,
                variationStep: null,
                variationInterval: 1000,
                decimalPlaces: 2
            };
            this.batchErrors = {
                nameTemplate: '',
                nodeIdTemplate: '',
                range: '',
                value: '',
                duplicates: []
            };
            if (this.batchAddModal) {
                this.batchAddModal.show();
            }
        },
        // 保存节点方法
        async saveNode(event) {
            event?.preventDefault();
            
            if (!this.validateNodeForm()) {
                return;
            }

            try {
                const url = this.isEditMode ? `/api/nodes/${this.currentNode.id}/` : '/api/nodes/';
                const method = this.isEditMode ? 'PUT' : 'POST';
                
                const response = await fetch(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken()
                    },
                    body: JSON.stringify(this.currentNode)
                });

                const data = await response.json();
                
                if (data.success) {
                    this.showSuccess(this.isEditMode ? '节点更新成功' : '节点添加成功');
                    await this.loadNodes();
                    this.modal.hide();
                } else {
                    this.showError(data.error || '操作失败');
                }
            } catch (error) {
                console.error('Error saving node:', error);
                this.showError('保存节点失败: ' + error.message);
            }
        },
        // 批量保存节点方法
        async saveBatchNodes(event) {
            event?.preventDefault();
            
            if (!this.validateBatchForm()) {
                return;
            }

            this.isProcessing = true;
            
            try {
                const response = await fetch('/api/nodes/batch/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken()
                    },
                    body: JSON.stringify(this.batchSettings)
                });

                const data = await response.json();
                
                if (data.success) {
                    this.showSuccess('批量添加节点成功');
                    await this.loadNodes();
                    this.batchAddModal.hide();
                } else {
                    this.showError(data.error || '批量添加失败');
                }
            } catch (error) {
                console.error('Error batch saving nodes:', error);
                this.showError('批量添加节点失败: ' + error.message);
            } finally {
                this.isProcessing = false;
            }
        },
        // 编辑节点方法
        editNode(node) {
            this.isEditMode = true;
            this.currentNode = { ...node };
            this.nodeIdError = '';
            this.formErrors = {
                name: '',
                nodeId: '',
                value: ''
            };
            if (this.modal) {
                this.modal.show();
            }
        },
        // 确认删除对话框
        confirmDelete(node) {
            this.confirmDialog = {
                title: '确认删除节点',
                message: '您确定要删除这个节点吗？此操作不可恢复。',
                type: 'danger',
                iconClass: 'bi-exclamation-triangle',
                confirmText: '删除',
                node: node,
                callback: () => this.deleteNode(node)
            };
            if (this.confirmModal) {
                this.confirmModal.show();
            }
        },
        // 处理确认对话框
        async handleConfirm() {
            if (this.confirmDialog.callback) {
                await this.confirmDialog.callback();
            }
            if (this.confirmModal) {
                this.confirmModal.hide();
            }
        },
        // 删除节点方法
        async deleteNode(node) {
            try {
                const response = await fetch(`/api/nodes/${node.id}/`, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': this.getCsrfToken()
                    }
                });

                if (response.ok) {
                    this.showSuccess('节点删除成功');
                    await this.loadNodes();
                } else {
                    const data = await response.json();
                    this.showError(data.error || '删除失败');
                }
            } catch (error) {
                console.error('Error deleting node:', error);
                this.showError('删除节点失败: ' + error.message);
            }
        },
        // 表单验证方法
        validateNodeForm() {
            let isValid = true;
            
            // 验证名称
            if (!this.currentNode.name) {
                this.formErrors.name = '请输入节点名称';
                isValid = false;
            }
            
            // 验证节点ID
            if (!this.currentNode.node_id) {
                this.formErrors.nodeId = '请输入节点ID';
                isValid = false;
            }
            
            // 验证值（仅对变量类型）
            if (this.currentNode.node_type === 'variable' && !this.currentNode.value) {
                this.formErrors.value = '请输入节点值';
                isValid = false;
            }
            
            return isValid;
        },
        validateBatchForm() {
            let isValid = true;
            
            // 验证名称模板
            if (!this.batchSettings.nameTemplate) {
                this.batchErrors.nameTemplate = '请输入节点名称模板';
                isValid = false;
            }
            
            // 验证节点ID模板
            if (!this.batchSettings.nodeIdTemplate) {
                this.batchErrors.nodeIdTemplate = '请输入节点ID模板';
                isValid = false;
            }
            
            // 验证范围
            if (this.batchSettings.startIndex > this.batchSettings.endIndex) {
                this.batchErrors.range = '起始序号不能大于结束序号';
                isValid = false;
            }
            
            return isValid;
        },
        // 错误提示相关方法
        showError(message) {
            this.showToast(message, 'danger');
        },
        showSuccess(message) {
            this.showToast(message, 'success');
        },
        showWarning(message) {
            this.showToast(message, 'warning');
        },
        showToast(message, type = 'info') {
            const toastContainer = document.querySelector('.toast-container');
            if (!toastContainer) return;
            
            const toast = document.createElement('div');
            toast.className = `toast align-items-center text-white bg-${type} border-0`;
            toast.setAttribute('role', 'alert');
            toast.setAttribute('aria-live', 'assertive');
            toast.setAttribute('aria-atomic', 'true');
            
            toast.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            `;
            
            toastContainer.appendChild(toast);
            const bsToast = new bootstrap.Toast(toast);
            bsToast.show();
            
            toast.addEventListener('hidden.bs.toast', () => {
                toast.remove();
            });
        },
        // 节点数据加载方法
        async loadNodes() {
            try {
                const response = await fetch('/api/nodes/');
                const data = await response.json();
                if (data.success) {
                    this.nodes = data.nodes;
                    this.error = null;
                } else {
                    this.error = '加载节点失败: ' + data.error;
                }
            } catch (error) {
                console.error('Error loading nodes:', error);
                this.error = '加载节点失败: ' + error.message;
            }
        },
        // 工具方法
        getNodeTypeDisplay(type) {
            return this.nodeTypes.find(t => t.value === type)?.label || type;
        },
        getDataTypeDisplay(type) {
            return this.dataTypes.find(t => t.value === type)?.label || type;
        },
        getVariationTypeDisplay(type) {
            return this.variationTypes.find(t => t.value === type)?.label || type;
        },
        getCsrfToken() {
            return document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        }
    },
    mounted() {
        try {
            // 获取预加载的数据
            const nodesData = document.getElementById('nodes-data');
            
            if (nodesData) {
                this.nodes = JSON.parse(nodesData.textContent);
            }
            
            // 初始化模态框
            const nodeModal = document.getElementById('nodeModal');
            const confirmModal = document.getElementById('confirmModal');
            const batchAddModal = document.getElementById('batchAddModal');
            
            if (nodeModal) this.modal = new bootstrap.Modal(nodeModal);
            if (confirmModal) this.confirmModal = new bootstrap.Modal(confirmModal);
            if (batchAddModal) this.batchAddModal = new bootstrap.Modal(batchAddModal);
            
            // 添加全局的toast容器
            const toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '1050';
            document.body.appendChild(toastContainer);
        } catch (error) {
            console.error('Error in mounted hook:', error);
            this.error = '初始化失败: ' + error.message;
        }
    }
});

// 挂载Vue应用
app.mount('#app'); 